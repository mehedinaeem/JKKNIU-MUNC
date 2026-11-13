from accounts.models import RateLimitCounter
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DatabaseError, connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image
from pypdf import PdfWriter
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from events.models import Event
from forms.models import FormField, RegistrationForm
from forms.services import publish_form
from .models import FormSubmission, SubmissionFile, UploadCleanup, SubmissionStatusChange
from .services import submit_application
from .storage import CloudinaryPrivateStorage


def pdf_bytes(active=False):
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    if active:
        from pypdf.generic import NameObject, DictionaryObject, TextStringObject
        writer.root_object[NameObject('/OpenAction')] = DictionaryObject({
            NameObject('/S'): NameObject('/JavaScript'), NameObject('/JS'): TextStringObject('unsafe-test-action')})
    writer.write(output)
    return output.getvalue()


def image_bytes():
    output = BytesIO()
    Image.new('RGB', (8, 8), 'red').save(output, format='PNG')
    return output.getvalue()


class SubmissionSetup:
    def setUp(self):
        cache.clear()
        RateLimitCounter.objects.all().delete()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage_settings = override_settings(LOCAL_PRIVATE_UPLOAD_ROOT=self.directory.name)
        self.storage_settings.enable()
        self.addCleanup(self.storage_settings.disable)
        self.client = APIClient()
        self.staff = get_user_model().objects.create_user(username='reviewer', is_staff=True, is_superuser=True, email='reviewer@example.com')
        self.member = get_user_model().objects.create_user(username='member', email='member@example.com')
        self.event = Event.objects.create(title='Future conference', slug='future', event_type='conference',
                                          status='published', start_date=timezone.now() + timedelta(days=30))
        self.form = RegistrationForm.objects.create(event=self.event, title='Application', slug='apply', form_type='custom')
        FormField.objects.create(form=self.form, key='name', label='Name', field_type='short_text', required=True)
        self.version = publish_form(self.form.pk)
        self.form.refresh_from_db()

    def data(self, **extra):
        return {'applicant_email': 'applicant@example.com', 'version': self.version.number,
                'answers': {'name': 'Private Applicant'}, **extra}

    def post(self, **extra):
        return self.client.post('/api/forms/apply/submit/', self.data(**extra), format='json')

    def add_file_field(self):
        FormField.objects.create(form=self.form, key='document', label='Document', field_type='file',
            required=True, allowed_extensions=['pdf', 'png', 'jpg', 'jpeg'], max_file_size=1024 * 1024)
        self.version = publish_form(self.form.pk)

    def multipart(self, upload, **extra):
        import json
        return self.client.post('/api/forms/apply/submit/',
            {'payload': json.dumps(self.data(**extra)), 'document': upload}, format='multipart')


@override_settings(DEBUG=True, SUBMISSION_RATE_PER_MINUTE=1000, SUBMISSION_RATE_PER_HOUR=1000, SUBMISSION_EMAIL_RATE_PER_HOUR=1000)
class PublicSubmissionTests(SubmissionSetup, TestCase):
    def test_anonymous_success_reference_only_and_no_pii_lookup(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(response.data), {'reference_number', 'message'})
        submission = FormSubmission.objects.get()
        self.assertEqual(response.data['reference_number'], submission.reference_number)
        self.assertTrue(submission.reference_number.startswith('JM-'))
        self.assertEqual(submission.status, 'submitted')
        self.assertEqual(submission.event_id, self.event.pk)
        self.assertEqual(submission.registration_form_id, self.form.pk)
        self.assertEqual(submission.form_version_id, self.version.pk)
        self.assertIsNone(submission.submitted_by)
        for path in (f'/api/submissions/{submission.reference_number}/', f'/api/submissions/{submission.pk}/'):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertNotIn('Private Applicant', str(response.data))
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_invalid_answers_email_schema_version_and_injected_status(self):
        for changes in ({'answers': {}}, {'applicant_email': 'bad'}, {'version': 999},
                        {'answers': {'name': 'Valid', 'unexpected': 'bad'}}, {'status': 'approved'}):
            self.assertEqual(self.post(**changes).status_code, 400, changes)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(self.form.submission_count, 0)

    def test_duplicate_email_is_case_insensitive_and_response_has_no_previous_data(self):
        first = self.post(applicant_email=' Applicant@Example.com ')
        self.assertEqual(first.status_code, 201)
        response = self.post(applicant_email='applicant@example.COM')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(first.data['reference_number'], str(response.data))
        self.assertNotIn('Private Applicant', str(response.data))
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.form.allow_multiple_submissions = True
        self.form.save()
        self.assertEqual(self.post().status_code, 201)
        self.form.refresh_from_db()
        self.assertEqual(self.form.submission_count, 2)

    def test_capacity_deadlines_draft_and_closed_form(self):
        self.form.closes_at = timezone.now() - timedelta(seconds=1)
        self.form.save()
        self.assertEqual(self.post().status_code, 400)
        self.form.closes_at = None
        self.form.capacity = 1
        self.form.save()
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post(applicant_email='other@example.com').status_code, 400)
        for status in ('draft', 'closed', 'archived'):
            self.form.status = status
            self.form.save()
            self.assertEqual(self.post().status_code, 404)
        self.assertEqual(FormSubmission.objects.count(), 1)

    def test_private_pdf_and_image_metadata_no_public_url(self):
        self.add_file_field()
        for index, (name, data, mime) in enumerate([
                ('../receipt.pdf', pdf_bytes(), 'application/pdf'),
                ('portrait.png', image_bytes(), 'image/png')]):
            response = self.multipart(SimpleUploadedFile(name, data, content_type=mime),
                                      applicant_email=f'person{index}@example.com')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertNotIn('download_url', str(response.data))
            self.assertNotIn('provider_file_id', str(response.data))
        stored = SubmissionFile.objects.first()
        self.assertEqual(stored.original_filename, 'receipt.pdf')
        self.assertEqual(stored.content_type, 'application/pdf')
        self.assertEqual(stored.file_size, len(pdf_bytes()))
        self.assertNotIn('receipt', stored.provider_file_id)
        self.assertTrue((Path(self.directory.name) / stored.provider_file_id).exists())
        self.assertEqual(UploadCleanup.objects.count(), 0)
        self.assertEqual(self.client.get(f'/api/submission-files/{stored.pk}/').status_code, 403)
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(f'/api/submission-files/{stored.pk}/').status_code, 403)
        self.client.force_authenticate(self.staff)
        response = self.client.get(f'/api/submission-files/{stored.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertNotIn('receipt', response['Content-Disposition'])
        b''.join(response.streaming_content)  # Let Django's test client close the streaming response safely.

    def test_invalid_extensions_mime_contents_active_pdf_and_sizes(self):
        self.add_file_field()
        files = [
            ('document.exe', pdf_bytes(), 'application/pdf'),
            ('document.pdf', pdf_bytes(), 'image/png'),
            ('document.pdf', b'%PDF-fake\n%%EOF', 'application/pdf'),
            ('document.png', pdf_bytes(), 'image/png'),
            ('document.pdf', pdf_bytes(active=True), 'application/pdf'),
            ('document.pdf', pdf_bytes() + b'0' * (1024 * 1024), 'application/pdf'),
        ]
        for name, data, mime in files:
            response = self.multipart(SimpleUploadedFile(name, data, content_type=mime))
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(SubmissionFile.objects.count(), 0)
        self.assertEqual(UploadCleanup.objects.count(), 0)

    def test_unknown_file_field_and_duplicate_multipart_files_rejected(self):
        self.add_file_field()
        import json
        response = self.client.post('/api/forms/apply/submit/', {
            'payload': json.dumps(self.data()),
            'unknown': SimpleUploadedFile('x.pdf', pdf_bytes(), content_type='application/pdf')}, format='multipart')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/forms/apply/submit/', {
            'payload': json.dumps(self.data()),
            'document': [SimpleUploadedFile('a.pdf', pdf_bytes(), content_type='application/pdf'),
                         SimpleUploadedFile('b.pdf', pdf_bytes(), content_type='application/pdf')]}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SubmissionFile.objects.count(), 0)

    def test_ip_and_email_rate_limits(self):
        with override_settings(SUBMISSION_RATE_PER_MINUTE=1):
            self.assertEqual(self.post(answers={}).status_code, 400)
            response = self.post(answers={})
            self.assertEqual(response.status_code, 429)
            self.assertIn('Retry-After', response)
        cache.clear()
        RateLimitCounter.objects.all().delete()
        with override_settings(SUBMISSION_EMAIL_RATE_PER_HOUR=1):
            self.assertEqual(self.post(answers={}).status_code, 400)
            self.assertEqual(self.post(answers={}).status_code, 429)

    def test_quota_cache_failure_and_production_database_fallback(self):
        with override_settings(RATE_LIMIT_BACKEND='redis', REDIS_URL='redis://test-only'), patch('accounts.rate_limits.cache.incr', side_effect=RuntimeError('secret connection string')):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret', str(response.data))
        with override_settings(DEBUG=False, REDIS_URL='', RATE_LIMIT_BACKEND='auto', SECURE_SSL_REDIRECT=False):
            self.assertEqual(self.post(answers={}).status_code, 400)

    def test_staff_list_detail_status_and_privacy(self):
        self.post()
        submission = FormSubmission.objects.get()
        for user in (None, self.member):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get('/api/admin/submissions/').status_code, 403)
            self.assertEqual(self.client.get(f'/api/admin/submissions/{submission.pk}/').status_code, 403)
            self.assertEqual(self.client.patch(f'/api/admin/submissions/{submission.pk}/status/',
                {'status': 'approved'}, format='json').status_code, 403)
        self.client.force_authenticate(self.staff)
        response = self.client.get('/api/admin/submissions/?status=submitted')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertNotIn('applicant_email', response.data['results'][0])
        self.assertNotIn('answers', response.data['results'][0])
        response = self.client.get(f'/api/admin/submissions/{submission.pk}/')
        self.assertEqual(response.data['applicant_email'], 'applicant@example.com')
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        for status in ('under_review', 'shortlisted', 'approved', 'rejected', 'waitlisted'):
            response = self.client.patch(f'/api/admin/submissions/{submission.pk}/status/', {'status': status}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(SubmissionStatusChange.objects.count(), 5)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'waitlisted')
        self.assertEqual(self.client.patch(f'/api/admin/submissions/{submission.pk}/status/',
            {'status': 'paid'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/admin/submissions/{submission.pk}/status/',
            {'status': 'approved', 'answers': {}}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/admin/submissions/?event=invalid').status_code, 400)

    def test_event_deletion_retains_submissions_with_conflict_response(self):
        self.post()
        self.client.force_authenticate(self.staff)
        response = self.client.delete(f'/api/admin/events/{self.event.pk}/')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_status_csrf_protection(self):
        self.post()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.staff)
        submission = FormSubmission.objects.get()
        self.assertEqual(client.patch(f'/api/admin/submissions/{submission.pk}/status/',
            {'status': 'approved'}, format='json').status_code, 403)

    def test_idempotent_retry_returns_original_receipt_even_after_close(self):
        import uuid
        key = str(uuid.uuid4())
        self.form.capacity = 1
        self.form.allow_multiple_submissions = True
        self.form.save()
        first = self.post(submission_key=key)
        self.assertEqual(first.status_code, 201)
        self.form.status = 'closed'
        self.form.save()
        self.event.status = 'cancelled'
        self.event.save()
        retry = self.post(submission_key=key)
        self.assertEqual(retry.status_code, 201, retry.data)
        self.assertEqual(retry.data, first.data)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.form.refresh_from_db()
        self.assertEqual(self.form.submission_count, 1)
        changed = self.post(submission_key=key, answers={'name': 'Changed applicant'})
        self.assertEqual(changed.status_code, 400)
        self.assertIn('submission_key', changed.data)
        self.assertNotIn(first.data['reference_number'], str(changed.data))

    def test_file_retry_does_not_upload_or_count_twice(self):
        import uuid
        self.add_file_field()
        key = str(uuid.uuid4())
        provider = Mock()
        provider.name = 'cloudinary'
        with patch('registrations.services.get_provider', return_value=provider):
            first = self.multipart(SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf'), submission_key=key)
            retry = self.multipart(SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf'), submission_key=key)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(retry.data, first.data)
        provider.upload.assert_called_once()
        self.assertEqual(SubmissionFile.objects.count(), 1)
        self.assertEqual(UploadCleanup.objects.count(), 0)

    def test_json_body_size_limit(self):
        response = self.post(answers={'name': 'a' * (2 * 1024 * 1024)})
        self.assertEqual(response.status_code, 413)

    def test_cloudinary_authenticated_upload_and_no_signed_url_in_responses(self):
        self.add_file_field()
        config = {'cloud_name': 'test-only-cloud', 'api_key': 'test-only-key', 'api_secret': 'test-only-secret'}
        def fake_upload(upload, **kwargs):
            self.assertEqual(kwargs['type'], 'authenticated')
            self.assertEqual(kwargs['resource_type'], 'raw')
            self.assertFalse(kwargs['overwrite'])
            return {'public_id': kwargs['public_id'], 'type': 'authenticated', 'resource_type': 'raw'}
        with override_settings(SUBMISSION_STORAGE_PROVIDER='cloudinary', CLOUDINARY_CONFIG=config), \
                patch('cloudinary.uploader.upload', side_effect=fake_upload) as upload:
            response = self.multipart(SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf'))
        self.assertEqual(response.status_code, 201, response.data)
        upload.assert_called_once()
        self.assertNotIn('secret', str(response.data))
        self.assertEqual(SubmissionFile.objects.get().storage_provider, 'cloudinary')
        remote = Mock(status_code=200)
        remote.iter_content.return_value = iter([pdf_bytes()])
        self.client.force_authenticate(self.staff)
        with override_settings(CLOUDINARY_CONFIG=config), patch('requests.get', return_value=remote) as fetch:
            stored = SubmissionFile.objects.get()
            response = self.client.get(f'/api/submission-files/{stored.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('Location', response)
            self.assertIn('type=authenticated', fetch.call_args.args[0])
            self.assertEqual(b''.join(response.streaming_content), pdf_bytes())
        remote.close.assert_called()

    def test_failed_upload_is_cleaned_and_database_rolls_back(self):
        self.add_file_field()
        provider = Mock(name='provider')
        provider.name = 'cloudinary'
        provider.upload.side_effect = RuntimeError('secret SDK details')
        with patch('registrations.services.get_provider', return_value=provider):
            response = self.multipart(SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf'))
        self.assertEqual(response.status_code, 503)
        provider.delete.assert_called_once()
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(UploadCleanup.objects.count(), 0)
        self.form.refresh_from_db()
        self.assertEqual(self.form.submission_count, 0)

    def test_database_error_after_upload_cleans_remote_asset(self):
        self.add_file_field()
        provider = Mock()
        provider.name = 'cloudinary'
        with patch('registrations.services.get_provider', return_value=provider), \
                patch.object(SubmissionFile.objects, 'create', side_effect=DatabaseError('private DB detail')):
            response = self.multipart(SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf'))
        self.assertEqual(response.status_code, 503)
        provider.upload.assert_called_once()
        provider.delete.assert_called_once()
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(UploadCleanup.objects.count(), 0)

    def test_failed_cleanup_retains_retryable_intent_and_command_retries(self):
        self.add_file_field()
        provider = Mock()
        provider.name = 'cloudinary'
        provider.upload.side_effect = RuntimeError('timeout after remote acceptance')
        provider.delete.side_effect = RuntimeError('network down')
        with patch('registrations.services.get_provider', return_value=provider):
            self.assertEqual(self.multipart(SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf')).status_code, 503)
        intent = UploadCleanup.objects.get()
        self.assertEqual(intent.attempts, 1)
        UploadCleanup.objects.filter(pk=intent.pk).update(created_at=timezone.now() - timedelta(hours=2))
        provider.delete.side_effect = None
        with patch('registrations.services.get_provider', return_value=provider):
            call_command('cleanup_uploads', stdout=StringIO())
        self.assertEqual(UploadCleanup.objects.count(), 0)

    def test_cleanup_never_deletes_committed_files(self):
        self.add_file_field()
        self.multipart(SimpleUploadedFile('receipt.pdf', pdf_bytes(), content_type='application/pdf'))
        stored = SubmissionFile.objects.get()
        intent = UploadCleanup.objects.create(storage_provider=stored.storage_provider, provider_file_id=stored.provider_file_id)
        UploadCleanup.objects.filter(pk=intent.pk).update(created_at=timezone.now() - timedelta(hours=2))
        with patch('registrations.services.get_provider') as provider:
            call_command('cleanup_uploads', stdout=StringIO())
        provider.assert_not_called()
        self.assertTrue((Path(self.directory.name) / stored.provider_file_id).exists())

    def test_production_temporary_storage_rejected(self):
        self.add_file_field()
        with override_settings(DEBUG=False, SUBMISSION_STORAGE_PROVIDER='temporary'):
            with self.assertRaises(APIException):
                submit_application(self.form.pk, 'new@example.com', self.version.number,
                    {'name': 'Valid'}, {'document': SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf')})
        self.assertEqual(FormSubmission.objects.count(), 0)


@override_settings(DEBUG=True)
class CommitFailureTests(SubmissionSetup, TransactionTestCase):
    def test_commit_failure_cleans_uploaded_asset_and_restores_capacity(self):
        self.add_file_field()
        provider = Mock()
        provider.name = 'cloudinary'
        with patch('registrations.services.get_provider', return_value=provider), \
                patch.object(connection, 'commit', side_effect=DatabaseError('commit failed')):
            with self.assertRaises(APIException):
                submit_application(self.form.pk, 'new@example.com', self.version.number,
                    {'name': 'Valid'}, {'document': SimpleUploadedFile('cv.pdf', pdf_bytes(), content_type='application/pdf')})
        provider.upload.assert_called_once()
        provider.delete.assert_called_once()
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(SubmissionFile.objects.count(), 0)
        self.assertEqual(UploadCleanup.objects.count(), 0)
        self.form.refresh_from_db()
        self.assertEqual(self.form.submission_count, 0)


class SubmissionMigrationTests(TransactionTestCase):
    def test_existing_submissions_are_preserved_and_backfilled(self):
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([('registrations', '0002_alter_submissionfile_file')])
            apps = executor.loader.project_state([('registrations', '0002_alter_submissionfile_file')]).apps
            user = apps.get_model('auth', 'User').objects.create(username='historical', email='History@Example.com')
            event = apps.get_model('events', 'Event').objects.create(title='Historical backend event',
                slug='historical-backend', event_type='custom', start_date=timezone.now())
            form = apps.get_model('club_forms', 'RegistrationForm').objects.create(event_id=event.pk,
                title='Old form', slug='old-form', form_type='custom')
            version = apps.get_model('club_forms', 'FormVersion').objects.create(form_id=form.pk, number=1,
                schema={'title': 'Immutable original', 'fields': []})
            old = apps.get_model('registrations', 'Submission').objects.create(version_id=version.pk,
                submitted_by_id=user.pk, answers={'historical': 'Preserve this value'})
            apps.get_model('registrations', 'SubmissionFile').objects.create(submission_id=old.pk,
                field_key='document', file='answers/legacy.pdf')
            original_id, original_timestamp = old.pk, old.created_at
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            updated = FormSubmission.objects.get(pk=original_id)
            self.assertEqual(updated.answers, {'historical': 'Preserve this value'})
            self.assertEqual(updated.submitted_at, original_timestamp)
            self.assertEqual(updated.applicant_email, 'history@example.com')
            self.assertEqual(updated.event_id, event.pk)
            self.assertEqual(updated.registration_form_id, form.pk)
            self.assertEqual(updated.form_version_id, version.pk)
            self.assertTrue(updated.reference_number.startswith('JM-'))
            self.assertEqual(updated.files.get().file.name, 'answers/legacy.pdf')
        finally:
            MigrationExecutor(connection).migrate(latest)
