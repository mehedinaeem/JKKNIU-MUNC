from accounts.models import RateLimitCounter
import copy
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as ModelValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from events.models import Event
from forms.models import FormField, FormVersion, RegistrationForm
from forms.serializers import FormFieldSerializer
from forms.services import publish_form, submit_form
from forms.validation import validate_answers
from registrations.models import Submission, SubmissionFile


def pdf_bytes():
    from io import BytesIO
    from pypdf import PdfWriter
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    return output.getvalue()


@override_settings(DEBUG=True, SUBMISSION_RATE_PER_MINUTE=1000, SUBMISSION_RATE_PER_HOUR=1000, SUBMISSION_EMAIL_RATE_PER_HOUR=1000)
class DynamicFormTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        RateLimitCounter.objects.all().delete()
        self.client = APIClient()
        self.staff = get_user_model().objects.create_user(username='form-staff', is_staff=True, is_superuser=True)
        self.user = get_user_model().objects.create_user(username='applicant', email='applicant@example.com')
        self.other = get_user_model().objects.create_user(username='other-applicant', email='other@example.com')
        self.event = Event.objects.create(title='Future', slug='future', status='published',
            event_type='custom', start_date=timezone.now() + timedelta(days=20))
        self.form = RegistrationForm.objects.create(event=self.event, title='Application', slug='application', form_type='custom')
        self.field = FormField.objects.create(form=self.form, key='name', label='Name', field_type='short_text', required=True)

    def auth_staff(self):
        self.client.force_authenticate(self.staff)

    def publish(self):
        version = publish_form(self.form.pk)
        self.form.refresh_from_db()
        return version

    def submit(self, answers=None, version=1):
        return self.client.post('/api/forms/application/submissions/',
            {'version': version, 'answers': {'name': 'Applicant'} if answers is None else answers}, format='json')

    def test_draft_visibility_and_event_scoping(self):
        self.assertEqual(self.client.get('/api/forms/application/').status_code, 404)
        self.assertEqual(self.client.get('/api/events/future/forms/').data['count'], 0)
        self.publish()
        self.assertEqual(self.client.get('/api/forms/application/').data['version'], 1)
        self.assertEqual(self.client.get('/api/events/future/forms/').data['count'], 1)
        self.event.status = 'draft'
        self.event.save()
        self.assertEqual(self.client.get('/api/forms/application/').status_code, 404)
        self.assertEqual(self.client.get('/api/events/future/forms/').status_code, 404)

    def test_staff_create_nested_update_reorder_delete_preview(self):
        self.auth_staff()
        data = {'event': self.event.pk, 'title': 'Custom', 'slug': 'custom', 'form_type': 'new-type',
                'fields': [{'key': 'email', 'label': 'Email', 'field_type': 'email', 'required': True},
                           {'key': 'age', 'label': 'Age', 'field_type': 'integer', 'display_order': 1}]}
        response = self.client.post('/api/admin/forms/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data['id']
        response = self.client.patch(f'/api/admin/forms/{pk}/', {'fields': [
            {'key': 'age', 'label': 'Age updated', 'field_type': 'integer', 'display_order': 0}]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data['fields']), 1)
        preview = self.client.get(f'/api/admin/forms/{pk}/preview/')
        self.assertEqual(preview.data['schema']['fields'][0]['key'], 'age')
        self.assertTrue(preview.data['draft'])
        response = self.client.post(f'/api/admin/forms/{pk}/publish/')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.patch(f'/api/admin/forms/{pk}/', {'status': 'closed'}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/forms/custom/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/admin/forms/{pk}/', {'status': 'archived'}, format='json').status_code, 200)

    def test_staff_permissions_all_routes(self):
        routes = [(self.client.post, '/api/admin/forms/'),
                  (self.client.patch, f'/api/admin/forms/{self.form.pk}/'),
                  (self.client.get, f'/api/admin/forms/{self.form.pk}/preview/'),
                  (self.client.post, f'/api/admin/forms/{self.form.pk}/publish/'),
                  (self.client.post, f'/api/admin/forms/{self.form.pk}/duplicate/')]
        inactive = get_user_model().objects.create_user(username='inactive-staff', is_staff=True, is_active=False)
        for user in (None, self.user, inactive):
            self.client.force_authenticate(user)
            for method, url in routes:
                self.assertEqual(method(url).status_code, 403)

    def test_duplicate_keys_rejected_atomically_and_unique_database_constraint(self):
        self.auth_staff()
        field = {'key': 'duplicate', 'label': 'Duplicate', 'field_type': 'short_text'}
        response = self.client.patch(f'/api/admin/forms/{self.form.pk}/', {'title': 'Should rollback', 'fields': [field, field]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.form.refresh_from_db()
        self.assertEqual(self.form.title, 'Application')
        self.assertEqual(self.form.fields.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FormField.objects.create(form=self.form, key='name', label='Duplicate', field_type='email')

    def test_incomplete_nested_patch_definition_is_rejected(self):
        self.auth_staff()
        response = self.client.patch(f'/api/admin/forms/{self.form.pk}/',
                                     {'fields': [{'key': 'name'}]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.form.fields.get().label, 'Name')

    def test_cannot_publish_via_status_or_publish_empty_form(self):
        self.auth_staff()
        response = self.client.patch(f'/api/admin/forms/{self.form.pk}/', {'status': 'published'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.form.fields.all().delete()
        self.assertEqual(self.client.post(f'/api/admin/forms/{self.form.pk}/publish/').status_code, 400)
        self.assertEqual(self.form.versions.count(), 0)

    def test_version_and_existing_response_preserved_after_edits(self):
        first = self.publish()
        original_schema = copy.deepcopy(first.schema)
        self.client.force_authenticate(self.user)
        response = self.submit()
        self.assertEqual(response.status_code, 201, response.data)
        submission = Submission.objects.get(pk=response.data['id'])
        self.auth_staff()
        response = self.client.patch(f'/api/admin/forms/{self.form.pk}/', {'title': 'New draft title', 'fields': [
            {'key': 'new_question', 'label': 'New', 'field_type': 'integer', 'required': True}]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get('/api/forms/application/').data['schema'], original_schema)
        second = self.publish()
        self.assertEqual(second.number, 2)
        first.refresh_from_db()
        submission.refresh_from_db()
        self.assertEqual(first.schema, original_schema)
        self.assertEqual(submission.version_id, first.pk)
        self.assertEqual(submission.answers, {'name': 'Applicant'})
        self.assertEqual(self.client.get('/api/forms/application/').data['schema']['title'], 'New draft title')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.submit(version=1).status_code, 400)
        self.assertEqual(self.submit({'new_question': 5}, version=2).status_code, 201)

    def test_version_mutation_and_field_key_change_blocked(self):
        version = self.publish()
        version.schema = {}
        with self.assertRaises(ModelValidationError):
            version.save()
        with self.assertRaises(ModelValidationError):
            FormVersion.objects.filter(pk=version.pk).update(schema={})
        with self.assertRaises(ModelValidationError):
            version.delete()
        with self.assertRaises(ModelValidationError):
            FormVersion.objects.filter(pk=version.pk).delete()
        self.field.key = 'renamed'
        with self.assertRaises(ModelValidationError):
            self.field.save()

    def test_duplicate_copies_draft_only_and_keeps_source(self):
        self.publish()
        self.auth_staff()
        response = self.client.post(f'/api/admin/forms/{self.form.pk}/duplicate/',
            {'title': 'Copy', 'slug': 'copy'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        clone = RegistrationForm.objects.get(pk=response.data['id'])
        self.assertEqual(clone.status, 'draft')
        self.assertEqual(clone.submission_count, 0)
        self.assertEqual(clone.versions.count(), 0)
        self.assertEqual(clone.fields.get().key, 'name')
        self.assertEqual(self.form.versions.count(), 1)
        self.assertEqual(self.client.post(f'/api/admin/forms/{self.form.pk}/duplicate/',
            {'title': 'Copy again', 'slug': 'copy'}, format='json').status_code, 400)

    def test_required_unknown_invalid_answers_and_unpublished_submission(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.submit().status_code, 404)
        self.publish()
        for answers in ({}, {'name': '  '}, {'name': 'Valid', 'injected': 'value'}, {'name': True}):
            self.assertEqual(self.submit(answers).status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)
        self.form.refresh_from_db()
        self.assertEqual(self.form.submission_count, 0)

    def test_all_deadlines_and_status_capacity_guards(self):
        self.publish()
        self.client.force_authenticate(self.user)
        now = timezone.now()
        for model, field, value in [
            (self.form, 'opens_at', now + timedelta(days=1)),
            (self.form, 'closes_at', now - timedelta(seconds=1)),
            (self.event, 'registration_start', now + timedelta(days=1)),
            (self.event, 'registration_end', now - timedelta(seconds=1)),
            (self.event, 'start_date', now - timedelta(seconds=1)),
        ]:
            original = getattr(model, field)
            setattr(model, field, value)
            model.save()
            self.assertEqual(self.submit().status_code, 400, field)
            setattr(model, field, original)
            model.save()
        for status in ('closed', 'archived', 'draft'):
            self.form.status = status
            self.form.save()
            self.assertEqual(self.submit().status_code, 404)
        self.form.status = 'published'
        self.form.capacity = 1
        self.form.save()
        self.assertEqual(self.submit().status_code, 201)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.submit().status_code, 400)
        self.assertEqual(Submission.objects.count(), 1)

    def test_duplicate_submissions_and_optional_multiple(self):
        self.publish()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.submit().status_code, 400)
        self.form.allow_multiple_submissions = True
        self.form.save()
        self.assertEqual(self.submit().status_code, 201)
        self.form.refresh_from_db()
        self.assertEqual(self.form.submission_count, 2)

    def test_submission_requires_authentication_and_csrf(self):
        self.publish()
        self.assertEqual(self.submit().status_code, 403)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/api/forms/application/submissions/',
            {'version': 1, 'answers': {'name': 'Valid'}}, format='json').status_code, 403)

    @override_settings(DEBUG=True)
    def test_private_upload_and_download_permissions(self):
        FormField.objects.create(form=self.form, key='document', label='Document', field_type='file',
            required=True, allowed_extensions=['pdf'], max_file_size=1024)
        self.publish()
        from registrations.models import PrivateUploadStorage
        with tempfile.TemporaryDirectory() as directory, override_settings(LOCAL_PRIVATE_UPLOAD_ROOT=directory):
            self.client.force_authenticate(self.user)
            response = self.client.post('/api/forms/application/submissions/', {
                'payload': '{"version":1,"answers":{"name":"Valid"}}',
                'document': SimpleUploadedFile('application.pdf', pdf_bytes(), content_type='application/pdf'),
            }, format='multipart')
            self.assertEqual(response.status_code, 201, response.data)
            stored = SubmissionFile.objects.get()
            self.assertNotIn('private_uploads', str(response.data))
            response = self.client.get(f'/api/submission-files/{stored.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/octet-stream')
            self.assertIn('attachment;', response['Content-Disposition'])
            b''.join(response.streaming_content)  # Let Django's test client close the streaming response safely.
            self.client.force_authenticate(self.other)
            self.assertEqual(self.client.get(f'/api/submission-files/{stored.pk}/').status_code, 403)
            self.auth_staff()
            response = self.client.get(f'/api/submission-files/{stored.pk}/')
            self.assertEqual(response.status_code, 200)
            b''.join(response.streaming_content)  # Let Django's test client close the streaming response safely.

    def test_bad_file_extension_size_and_fake_path(self):
        field = {'key': 'file', 'label': 'File', 'field_type': 'file', 'required': True,
                 'allowed_extensions': ['pdf'], 'max_file_size': 4}
        for value in ('/etc/passwd', SimpleUploadedFile('x.html', b'123'), SimpleUploadedFile('x.pdf', b'12345')):
            with self.assertRaises(ValidationError):
                validate_answers({'fields': [field]}, {'file': value})

    def test_production_file_uploads_fail_closed(self):
        FormField.objects.create(form=self.form, key='document', label='File', field_type='file',
                                 allowed_extensions=['pdf'], max_file_size=100)
        self.publish()
        with override_settings(DEBUG=False):
            with self.assertRaises(ValidationError):
                submit_form(self.form.pk, self.user, 1, {'name': 'Valid'},
                            {'document': SimpleUploadedFile('x.pdf', b'123')})
        self.assertEqual(Submission.objects.count(), 0)


class FieldValidationTests(TestCase):
    def field(self, kind, **extra):
        data = {'key': 'answer', 'label': 'Question', 'field_type': kind, 'required': True, **extra}
        serializer = FormFieldSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return {**data, **serializer.validated_data}

    def test_supported_types_valid_and_invalid_answers(self):
        choices = [{'value': 'a', 'label': 'Option A'}, {'value': 'b', 'label': 'Option B'}]
        cases = [
            ('short_text', 'Valid', 123, {}), ('long_text', 'Detailed text', {}, {}),
            ('email', 'user@example.com', 'not-email', {}),
            ('phone', '+880 1712-345678', 'call me maybe', {}),
            ('integer', 4, 4.2, {'validation': {'min_value': 1, 'max_value': 5}}),
            ('decimal', '2.50', 'NaN', {'validation': {'min_value': '0', 'max_value': '3'}}),
            ('date', '2027-01-01', '2027-02-30', {}),
            ('dropdown', 'a', 'x', {'options': choices}), ('radio', 'b', ['a'], {'options': choices}),
            ('checkboxes', ['a', 'b'], ['a', 'x'], {'options': choices}),
            ('url', 'https://example.com', 'javascript:alert(1)', {}), ('consent', True, False, {}),
        ]
        for kind, valid, invalid, extra in cases:
            with self.subTest(kind=kind):
                schema = {'fields': [self.field(kind, **extra)]}
                validate_answers(schema, {'answer': valid})
                with self.assertRaises(ValidationError):
                    validate_answers(schema, {'answer': invalid})

    def test_definition_rules_defaults_and_options(self):
        cases = [
            {'field_type': 'short_text', 'validation': {'expression': 'eval(x)'}},
            {'field_type': 'short_text', 'validation': {'min_length': 5, 'max_length': 1}},
            {'field_type': 'date', 'validation': {'min_date': 'yesterday'}},
            {'field_type': 'integer', 'default_value': 'not integer'},
            {'field_type': 'decimal', 'validation': {'min_value': 'NaN'}},
            {'field_type': 'dropdown', 'options': []},
            {'field_type': 'radio', 'options': [{'value': 'a', 'label': 'A'}, {'value': 'a', 'label': 'Again'}]},
            {'field_type': 'file', 'allowed_extensions': ['html'], 'max_file_size': 1024},
            {'field_type': 'file', 'allowed_extensions': ['pdf'], 'max_file_size': 99999999},
            {'field_type': 'consent', 'default_value': True},
        ]
        for extra in cases:
            serializer = FormFieldSerializer(data={'key': 'answer', 'label': 'Question', **extra})
            self.assertFalse(serializer.is_valid(), extra)

    def test_defaults_are_display_hints_not_required_answer_substitutes(self):
        field = self.field('short_text', default_value='Example answer')
        with self.assertRaises(ValidationError):
            validate_answers({'fields': [field]}, {})
        clean, files = validate_answers({'fields': [{**field, 'required': False}]}, {})
        self.assertEqual(clean, {})
        self.assertEqual(files, {})

    def test_optional_fields_still_reject_wrong_answer_types(self):
        field = self.field('integer', required=False)
        with self.assertRaises(ValidationError):
            validate_answers({'fields': [field]}, {'answer': []})
