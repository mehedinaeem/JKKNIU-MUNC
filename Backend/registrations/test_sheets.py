from datetime import timedelta
from io import BytesIO
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from accounts.models import EventAssignment
from accounts.roles import setup_roles
from events.models import Event
from forms.models import RegistrationForm, FormField
from forms.services import publish_form
from .models import FormSubmission, SubmissionFile, ReviewAccessLog


class FormSheetTests(TestCase):
    def setUp(self):
        setup_roles()
        self.client = APIClient()
        self.event = Event.objects.create(title='Assigned', slug='sheet-event', event_type='conference', status='published', start_date=timezone.now() + timedelta(days=30))
        self.form = RegistrationForm.objects.create(event=self.event, title='Delegate sheet', slug='sheet-delegate', form_type='delegate')
        self.name = FormField.objects.create(form=self.form, key='name', label='Original full name', field_type='short_text')
        FormField.objects.create(form=self.form, key='choice', label='Committee', field_type='radio', options=[{'value': 'a', 'label': 'Original committee'}])
        FormField.objects.create(form=self.form, key='photo', label='Photo', field_type='file', allowed_extensions=['png'], max_file_size=1048576)
        self.first_version = publish_form(self.form.pk)
        self.first = FormSubmission.objects.create(event=self.event, registration_form=self.form, form_version=self.first_version, applicant_email='first@example.com', answers={'name': 'First applicant', 'choice': 'a'})
        self.photo = SubmissionFile.objects.create(submission=self.first, field_key='photo', storage_provider='temporary', provider_file_id='applications/' + 'a'*32 + '.png', original_filename='photo.png', content_type='image/png', file_size=100)
        self.name.label = 'Preferred name'
        self.name.save()
        FormField.objects.filter(form=self.form, key='choice').delete()
        FormField.objects.create(form=self.form, key='institution', label='Institution', field_type='short_text')
        self.second_version = publish_form(self.form.pk)
        self.second = FormSubmission.objects.create(event=self.event, registration_form=self.form, form_version=self.second_version, applicant_email='second@example.com', answers={'name': 'Second applicant', 'institution': 'University'}, status='approved')
        other = Event.objects.create(title='Unassigned', slug='unassigned-sheet', event_type='conference', start_date=timezone.now())
        self.hidden_form = RegistrationForm.objects.create(event=other, title='Secret', slug='secret-sheet', form_type='custom')
        self.reviewer = get_user_model().objects.create_user('sheet-reviewer', is_staff=True)
        self.reviewer.groups.add(Group.objects.get(name='Reviewer'))
        self.manager = get_user_model().objects.create_user('sheet-manager', is_staff=True)
        self.manager.groups.add(Group.objects.get(name='Event Admin'))
        self.root = get_user_model().objects.create_user('sheet-root', is_staff=True, is_superuser=True)
        for user in (self.reviewer, self.manager):
            EventAssignment.objects.create(user=user, event=self.event)
        self.path = f'/api/admin/forms/{self.form.pk}/sheet/'
        self.preview = f'/api/submission-files/{self.photo.pk}/preview/'

    def test_sheet_rows_include_all_version_fields_without_mixing_forms(self):
        for user in (self.reviewer, self.manager, self.root):
            self.client.force_authenticate(user)
            response = self.client.get(self.path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['count'], 2)
            self.assertEqual({field['key'] for field in response.data['columns']}, {'name', 'choice', 'photo', 'institution'})
            self.assertEqual(next(field['label'] for field in response.data['columns'] if field['key'] == 'name'), 'Preferred name')
            first = next(row for row in response.data['results'] if row['id'] == str(self.first.pk))
            self.assertEqual(first['applicant_email'], 'first@example.com')
            self.assertEqual(first['schema_version'], 1)
            self.assertEqual(first['form_schema']['fields'][0]['label'], 'Original full name')
            self.assertEqual(first['files'][0]['id'], self.photo.pk)
            self.assertNotIn('provider_file_id', str(response.data))
            self.assertIn('no-store', response['Cache-Control'])
            empty = self.client.get(self.path, {'registration_form': self.hidden_form.pk})
            self.assertEqual(empty.data['count'], 0)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(self.path, {'search': 'Second applicant'}).data['count'], 1)
        self.assertEqual(self.client.get(self.path, {'status': 'approved'}).data['count'], 1)

    def test_sheet_permission_and_revoked_assignment(self):
        plain = get_user_model().objects.create_user('sheet-plain', is_staff=True)
        for user in (None, plain):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.path).status_code, 403)
            self.assertEqual(self.client.get(self.preview).status_code, 403)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(f'/api/admin/forms/{self.hidden_form.pk}/sheet/').status_code, 404)
        EventAssignment.objects.filter(user=self.reviewer).delete()
        self.assertEqual(self.client.get(self.path).status_code, 404)
        self.assertEqual(self.client.get(self.preview).status_code, 403)

    def test_sheet_paginates_and_keeps_question_columns_stable(self):
        FormSubmission.objects.bulk_create([FormSubmission(event=self.event, registration_form=self.form, form_version=self.second_version, applicant_email=f'user{i}@example.com', answers={'name': f'Applicant {i}'}) for i in range(25)])
        self.client.force_authenticate(self.reviewer)
        first = self.client.get(self.path)
        second = self.client.get(self.path, {'page': 2})
        self.assertEqual(first.data['count'], 27)
        self.assertEqual(first.data['columns'], second.data['columns'])
        self.assertEqual(second.data['page_number'], 2)
        self.assertIsNotNone(first.data['next'])
        self.assertLess(len(first.data['results']), 27)

    def test_image_previews_are_bounded_reencoded_private_and_audited(self):
        self.client.force_authenticate(self.reviewer)
        image = BytesIO()
        Image.new('RGB', (800, 600), 'navy').save(image, format='PNG')
        provider = Mock()
        provider.open.side_effect = lambda file_id: BytesIO(image.getvalue())
        with patch('registrations.views.get_provider', return_value=provider):
            for size, maximum in (('thumbnail', 160), ('large', 1200)):
                response = self.client.get(self.preview, {'size': size})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'image/png')
                self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
                self.assertIn('no-store', response['Cache-Control'])
                with Image.open(BytesIO(response.content)) as thumbnail:
                    self.assertLessEqual(max(thumbnail.size), maximum)
            self.assertEqual(ReviewAccessLog.objects.filter(action='file_preview', actor=self.reviewer).count(), 2)
            EventAssignment.objects.filter(user=self.reviewer).delete()
            self.assertEqual(self.client.get(self.preview).status_code, 403)
            self.assertEqual(provider.open.call_count, 2)

    def test_non_images_corrupt_files_and_legacy_uploads_are_not_executed(self):
        self.client.force_authenticate(self.reviewer)
        for changes in ({'content_type': 'application/pdf'}, {'content_type': 'image/svg+xml'}, {'storage_provider': 'legacy_local'}):
            SubmissionFile.objects.filter(pk=self.photo.pk).update(**changes)
            with patch('registrations.views.get_provider') as provider:
                self.assertEqual(self.client.get(self.preview).status_code, 400)
                provider.assert_not_called()
            SubmissionFile.objects.filter(pk=self.photo.pk).update(content_type='image/png', storage_provider='temporary')
        provider = Mock()
        provider.open.return_value = BytesIO(b'<script>not an image</script>')
        with patch('registrations.views.get_provider', return_value=provider):
            self.assertEqual(self.client.get(self.preview).status_code, 503)
        self.assertEqual(self.client.get(self.preview, {'size': 'unbounded'}).status_code, 400)
        self.assertFalse(ReviewAccessLog.objects.exists())
