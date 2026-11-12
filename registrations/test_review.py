from datetime import timedelta
from io import BytesIO
from unittest.mock import patch, Mock
from zipfile import ZipFile
from xml.etree import ElementTree
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import EventAssignment
from accounts.roles import setup_roles
from events.models import Event
from forms.models import RegistrationForm, FormField
from forms.services import publish_form
from .models import FormSubmission, ReviewerNote, SubmissionStatusChange, ReviewAccessLog, SubmissionFile
from .exports import safe_cell


class ReviewTests(TestCase):
    def setUp(self):
        cache.clear()
        setup_roles()
        self.client = APIClient()
        self.event = Event.objects.create(title='Assigned conference', slug='assigned', event_type='conference', status='published', start_date=timezone.now() + timedelta(days=30))
        self.other = Event.objects.create(title='Other conference', slug='other', event_type='conference', status='published', start_date=timezone.now() + timedelta(days=60))
        self.form = RegistrationForm.objects.create(event=self.event, title='Delegates', slug='delegates', form_type='custom')
        FormField.objects.create(form=self.form, key='custom_name', label='Full name', field_type='short_text')
        self.version = publish_form(self.form.pk)
        self.submission = FormSubmission.objects.create(event=self.event, registration_form=self.form, form_version=self.version, applicant_email='applicant@example.com', answers={'custom_name': '=HYPERLINK("unsafe")'})
        self.other_form = RegistrationForm.objects.create(event=self.other, title='Other form', slug='other-form', form_type='custom')
        FormField.objects.create(form=self.other_form, key='name', label='Name', field_type='short_text')
        self.other_version = publish_form(self.other_form.pk)
        self.other_submission = FormSubmission.objects.create(event=self.other, registration_form=self.other_form, form_version=self.other_version, applicant_email='hidden@example.com', answers={'name': 'Hidden Person'})
        users = get_user_model()
        self.superuser = users.objects.create_superuser('root', 'root@example.com', 'test-password')
        self.manager = users.objects.create_user('manager', is_staff=True)
        self.manager.groups.add(Group.objects.get(name='Event Admin'))
        self.reviewer = users.objects.create_user('reviewer', is_staff=True)
        self.reviewer.groups.add(Group.objects.get(name='Reviewer'))
        for user in (self.manager, self.reviewer):
            EventAssignment.objects.create(user=user, event=self.event)
        self.detail = f'/api/admin/submissions/{self.submission.pk}/'
        self.hidden_detail = f'/api/admin/submissions/{self.other_submission.pk}/'

    def test_role_scope_for_dashboard_search_details_and_exports(self):
        for user, expected in ((self.reviewer, 1), (self.manager, 1), (self.superuser, 2)):
            self.client.force_authenticate(user)
            metrics = self.client.get('/api/admin/dashboard/')
            self.assertEqual(metrics.status_code, 200)
            self.assertEqual(metrics.data['total_events'], expected)
            self.assertEqual(metrics.data['total_submissions'], expected)
            self.assertEqual(metrics.data['published_forms'], expected)
            self.assertEqual(metrics.data['statuses']['submitted'], expected)
            listed = self.client.get('/api/admin/submissions/')
            self.assertEqual(listed.data['count'], expected)
            self.assertEqual(self.client.get(self.hidden_detail).status_code, 200 if expected == 2 else 404)
            export = self.client.get('/api/admin/submissions/export/')
            self.assertEqual(export.status_code, 200)
            self.assertEqual(b'hidden@example.com' in export.content, expected == 2)
            self.assertIn('private', export['Cache-Control'])
            self.assertIn('no-store', export['Cache-Control'])
        self.client.force_authenticate(self.reviewer)
        for search in ('applicant@example.com', 'HYPERLINK', self.submission.reference_number):
            self.assertEqual(self.client.get('/api/admin/submissions/', {'search': search}).data['count'], 1)
        self.assertEqual(self.client.get('/api/admin/submissions/', {'search': 'Hidden Person'}).data['count'], 0)
        for query in ({'event': self.other.pk}, {'registration_form': self.other_form.pk}, {'status': 'approved'}):
            self.assertEqual(self.client.get('/api/admin/submissions/', query).data['count'], 0)
        for query in ({'event': 'bad'}, {'registration_form': '-1'}, {'status': 'bad'}, {'ordering': 'answers'}, {'search': 'x' * 201}):
            self.assertEqual(self.client.get('/api/admin/submissions/', query).status_code, 400)

    def test_private_append_only_notes_and_status_audits(self):
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.post(self.detail + 'notes/', {'body': 'Private assessment'}, format='json').status_code, 201)
        self.assertEqual(self.client.post(self.detail + 'notes/', {'body': 'Forged author', 'author': self.superuser.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.detail + 'notes/', {'body': 'overwrite'}, format='json').status_code, 405)
        for status in ('under_review', 'approved', 'approved'):
            self.assertEqual(self.client.patch(self.detail + 'status/', {'status': status}, format='json').status_code, 200)
        data = self.client.get(self.detail).data
        self.assertEqual(len(data['history']), 2)
        self.assertEqual(len(data['reviewer_notes']), 1)
        self.assertEqual(data['reviewer_notes'][0]['author_name'], 'reviewer')
        self.assertEqual(data['history'][0]['actor'], 'reviewer')
        self.assertEqual(SubmissionStatusChange.objects.count(), 2)
        self.assertEqual(ReviewerNote.objects.get().author_id, self.reviewer.pk)
        self.assertEqual(self.client.post(self.hidden_detail + 'notes/', {'body': 'Unauthorized'}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(self.hidden_detail + 'status/', {'status': 'rejected'}, format='json').status_code, 404)
        public = self.client.get('/api/forms/delegates/').data
        self.assertNotIn('Private assessment', str(public))
        self.assertNotIn('applicant@example.com', str(public))

    def test_anonymous_plain_staff_and_revoked_assignments_cannot_access_review(self):
        plain = get_user_model().objects.create_user('plain', is_staff=True)
        for user in (None, plain):
            self.client.force_authenticate(user)
            for path in ('/api/admin/dashboard/', '/api/admin/submissions/', self.detail, '/api/admin/submissions/export/', '/api/admin/review/forms/'):
                self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.post(self.detail + 'notes/', {'body': 'bad'}, format='json').status_code, 403)
        self.client.force_authenticate(self.reviewer)
        EventAssignment.objects.filter(user=self.reviewer).delete()
        self.assertEqual(self.client.get(self.detail).status_code, 404)
        self.assertEqual(self.client.get('/api/admin/dashboard/').data['total_submissions'], 0)
        self.assertNotIn('applicant@example.com', self.client.get('/api/admin/submissions/export/').content.decode())

    def test_csv_xlsx_formula_safety_and_historical_schema(self):
        self.client.force_authenticate(self.reviewer)
        FormField.objects.filter(form=self.form).update(label='Changed current label')
        publish_form(self.form.pk)
        csv_response = self.client.get('/api/admin/submissions/export/', {'file_format': 'csv'})
        self.assertIn(b"'=HYPERLINK", csv_response.content)
        self.assertIn(b'Full name', csv_response.content)
        self.assertNotIn(b'Changed current label', csv_response.content)
        xlsx_response = self.client.get('/api/admin/submissions/export/', {'file_format': 'xlsx'})
        self.assertEqual(xlsx_response.status_code, 200)
        with ZipFile(BytesIO(xlsx_response.content)) as archive:
            for path in archive.namelist():
                ElementTree.fromstring(archive.read(path))
            sheet = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            self.assertFalse(sheet.findall('.//s:f', ns))
            self.assertTrue(all(cell.attrib['t'] == 'inlineStr' for cell in sheet.findall('.//s:c', ns)))
            self.assertNotIn('hidden@example.com', archive.read('xl/worksheets/sheet1.xml').decode())
        self.assertEqual(ReviewAccessLog.objects.filter(actor=self.reviewer).count(), 2)
        for value in ('=1+1', '+SUM(A1)', '-1', '@SUM(A1)', '  =1', '\t=1', '\r=1', '＝1'):
            self.assertTrue(safe_cell(value).startswith("'"), value)
        self.assertEqual(self.client.get('/api/admin/submissions/export/', {'file_format': 'pdf'}).status_code, 400)
        with patch('registrations.exports.MAX_ROWS', 0):
            self.assertEqual(self.client.get('/api/admin/submissions/export/').status_code, 400)
        with patch('registrations.exports.MAX_CELLS', 1):
            self.assertEqual(self.client.get('/api/admin/submissions/export/').status_code, 400)

    def test_files_authorized_and_audited_without_provider_url(self):
        file = SubmissionFile.objects.create(submission=self.submission, field_key='file', storage_provider='temporary', provider_file_id='private-test', original_filename='cv.pdf')
        path = f'/api/submission-files/{file.pk}/'
        provider = Mock()
        provider.open.return_value = BytesIO(b'private-file')
        with patch('registrations.views.get_provider', return_value=provider):
            self.client.force_authenticate(self.reviewer)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'private-file')
            self.assertEqual(ReviewAccessLog.objects.get().submission_id, self.submission.pk)
            EventAssignment.objects.filter(user=self.reviewer).delete()
            self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(provider.open.call_count, 1)

    def test_cross_event_duplication_and_safe_archive(self):
        self.client.force_authenticate(self.manager)
        url = f'/api/admin/forms/{self.form.pk}/duplicate/'
        payload = {'title': 'Copied form', 'slug': 'copied-form', 'event': self.other.pk}
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 403)
        self.client.force_authenticate(self.superuser)
        self.form.opens_at = timezone.now() - timedelta(days=1)
        self.form.closes_at = timezone.now() + timedelta(days=1)
        self.form.save()
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        copied = RegistrationForm.objects.get(pk=response.data['id'])
        self.assertEqual(copied.event_id, self.other.pk)
        self.assertEqual(copied.status, 'draft')
        self.assertIsNone(copied.opens_at)
        self.assertIsNone(copied.closes_at)
        self.assertEqual(copied.submission_count, 0)
        self.assertEqual(copied.versions.count(), 0)
        self.assertEqual(copied.fields.count(), self.form.fields.count())
        response = self.client.patch(f'/api/admin/forms/{self.form.pk}/', {'status': 'archived'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/forms/delegates/').status_code, 404)
        self.assertEqual(self.client.get(self.detail).status_code, 200)
        self.assertTrue(FormSubmission.objects.filter(pk=self.submission.pk).exists())

    def test_review_writes_require_csrf_for_session_authentication(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.reviewer)
        for method, path, payload in (('post', self.detail + 'notes/', {'body': 'unsafe'}), ('patch', self.detail + 'status/', {'status': 'approved'})):
            self.assertEqual(getattr(client, method)(path, payload, format='json').status_code, 403)
        self.assertFalse(ReviewerNote.objects.exists())
        self.assertFalse(SubmissionStatusChange.objects.exists())

    def test_server_pagination_and_filtered_exports_include_all_pages(self):
        self.client.force_authenticate(self.reviewer)
        FormSubmission.objects.bulk_create([FormSubmission(event=self.event, registration_form=self.form,
            form_version=self.version, applicant_email=f'pagination{index}@example.com', answers={'custom_name': f'Applicant {index}'})
            for index in range(30)])
        response = self.client.get('/api/admin/submissions/', {'event': self.event.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 31)
        self.assertIsNotNone(response.data['next'])
        self.assertLess(len(response.data['results']), 31)
        last = self.client.get('/api/admin/submissions/', {'event': self.event.pk, 'page': 2})
        self.assertEqual(last.status_code, 200)
        export = self.client.get('/api/admin/submissions/export/', {'event': self.event.pk, 'page': 2})
        self.assertEqual(export.status_code, 200)
        self.assertIn(b'pagination0@example.com', export.content)
        self.assertIn(b'pagination29@example.com', export.content)
        self.assertEqual(ReviewAccessLog.objects.get().metadata['rows'], 31)

    def test_unicode_names_are_searchable_in_json_answers(self):
        self.submission.answers = {'custom_name': 'মেহেদী হাসান'}
        self.submission.save()
        self.client.force_authenticate(self.reviewer)
        response = self.client.get('/api/admin/submissions/', {'search': 'মেহেদী'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
