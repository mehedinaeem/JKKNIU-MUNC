from datetime import timedelta
from io import StringIO
import uuid
from unittest import skipUnless
from unittest.mock import Mock, patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import signing
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
import requests
from accounts.models import EventAssignment
from accounts.roles import setup_roles
from events.models import Event
from forms.models import RegistrationForm, FormField
from forms.services import publish_form
from registrations.models import FormSubmission, SubmissionStatusChange
from registrations.services import submit_application
from .models import EmailMessage, EmailCampaign, EmailTemplate, EmailDailyQuota, EmailDeliveryAttempt, EmailPreference, EmailWebhookEvent, EmailSystemState, EventEmailSettings, PaymentVerification, PaymentChange
from .notifications import queue_notification, reconcile
from .providers import BrevoProvider, SendResult
from .queue import process, claim, finish, quota_day
from .campaigns import activate_campaign, activate_due, recipients
from .rendering import render, validate_content

EMAIL_TEST = dict(EMAIL_ENABLED=True, BREVO_API_KEY='test-only-key', BREVO_WEBHOOK_TOKEN='test-only-webhook',
    DEFAULT_FROM_EMAIL='verified@example.invalid', PUBLIC_SITE_URL='https://munc.example.invalid', PUBLIC_API_URL='https://munc.example.invalid/api',
    EMAIL_RATE_PER_MINUTE=1000000000, EMAIL_DAILY_LIMIT=300, EMAIL_TRANSACTIONAL_RESERVE=50, EMAIL_MAX_ATTEMPTS=2, EMAIL_RETRY_BASE_SECONDS=1)


class EmailSetup:
    def setUp(self):
        setup_roles()
        EmailSystemState.objects.update_or_create(pk=1, defaults={'created_at': timezone.now()-timedelta(days=1)})
        self.client = APIClient()
        self.root = get_user_model().objects.create_user('email-root', email='admin@example.invalid', is_staff=True, is_superuser=True)
        self.client.force_authenticate(self.root)
        self.event = Event.objects.create(title='National MUN', slug='email-mun', event_type='conference', status='published', start_date=timezone.now()+timedelta(days=30))
        self.form = RegistrationForm.objects.create(event=self.event, title='Delegate Registration', slug='email-delegate', form_type='delegate', status='draft', allow_multiple_submissions=True)
        FormField.objects.create(form=self.form, key='full_name', label='Full name', field_type='short_text', required=True)
        self.version = publish_form(self.form.pk)
        self.submission = self.make_submission()
        self.job = queue_notification('registration', self.submission.pk)

    def make_submission(self, email='applicant@example.invalid', name='Example Applicant', form=None, version=None):
        return FormSubmission.objects.create(event=self.event, registration_form=form or self.form, form_version=version or self.version,
            applicant_email=email, answers={'full_name': name})

    def campaign(self, **changes):
        values = {'event': self.event, 'name': 'Event update', 'subject': 'Hello {{full_name}}', 'html_content': '<p>Hello {{full_name}}</p>',
            'text_content': 'Hello {{full_name}}', 'recipient_filter': {}, 'created_by': self.root}
        values.update(changes)
        return EmailCampaign.objects.create(**values)

    def quiet(self):
        EmailMessage.objects.all().update(status='skipped')

    def accepted(self):
        response = Mock(status_code=201)
        response.json.return_value = {'messageId': f'<{uuid.uuid4()}@brevo.test>'}
        return response


@override_settings(**EMAIL_TEST)
class EmailTests(EmailSetup, TestCase):
    def test_registration_confirmation_snapshot_and_idempotency_for_all_form_types(self):
        self.assertEqual(self.job.message_type, 'registration_confirmation')
        self.assertIn('Registration Received', self.job.subject)
        self.assertIn(self.submission.reference_number, self.job.text_content)
        self.assertIn('does not confirm selection or payment verification', self.job.text_content)
        self.assertIn('https://munc.example.invalid/events/email-mun', self.job.text_content)
        queue_notification('registration', self.submission.pk)
        self.assertEqual(EmailMessage.objects.count(), 1)
        for kind in ('executive-board', 'custom-new-type'):
            form = RegistrationForm.objects.create(event=self.event, title=kind, slug=kind, form_type=kind)
            FormField.objects.create(form=form, key='full_name', label='Full name', field_type='short_text')
            version = publish_form(form.pk)
            submission = self.make_submission(email=f'{kind}@example.invalid', form=form, version=version)
            job = queue_notification('registration', submission.pk)
            self.assertIn(kind, job.text_content)
            self.assertEqual(job.submission_id, submission.pk)

    def test_meaningful_status_transitions_and_event_instructions(self):
        EventEmailSettings.objects.create(event=self.event, status_notifications=['approved'], next_instructions='General instructions', status_instructions={'approved': 'Attend the briefing.'})
        with self.captureOnCommitCallbacks(execute=True):
            for _ in range(2):
                response = self.client.patch(f'/api/admin/submissions/{self.submission.pk}/status/', {'status': 'approved'}, format='json')
                self.assertEqual(response.status_code, 200)
        self.assertEqual(SubmissionStatusChange.objects.count(), 1)
        job = EmailMessage.objects.get(message_type='application_approved')
        self.assertIn('Attend the briefing.', job.text_content)
        self.assertIn('Approved', job.text_content)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f'/api/admin/submissions/{self.submission.pk}/status/', {'status': 'rejected'}, format='json')
        self.assertEqual(EmailMessage.objects.get(message_type='application_rejected').status, 'skipped')

    def test_only_managers_verify_payment_and_status_is_separate(self):
        reviewer = get_user_model().objects.create_user('pay-reviewer', is_staff=True)
        reviewer.groups.add(Group.objects.get(name='Reviewer'))
        EventAssignment.objects.create(user=reviewer, event=self.event)
        path = f'/api/admin/email/payments/{self.submission.pk}/'
        self.client.force_authenticate(reviewer)
        self.assertEqual(self.client.patch(path, {'status': 'verified'}, format='json').status_code, 403)
        self.client.force_authenticate(self.root)
        with self.captureOnCommitCallbacks(execute=True):
            for _ in range(2):
                result = self.client.patch(path, {'status': 'verified', 'amount': '1500.00', 'currency': 'BDT', 'next_instructions': 'Keep your reference.'}, format='json')
                self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(PaymentChange.objects.count(), 1)
        self.assertEqual(PaymentVerification.objects.get().verified_by, self.root)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'submitted')
        message = EmailMessage.objects.get(message_type='payment_verified')
        self.assertIn('BDT 1500.00', message.text_content)
        self.assertIn('Keep your reference.', message.text_content)
        self.assertEqual(message.attempt_count, 0)
        self.assertEqual(self.client.patch(path, {'status': 'verified', 'amount': '2000', 'currency': 'BDT'}, format='json').status_code, 400)

    def test_bulk_snapshot_deduplicates_normalized_email_and_is_fixed(self):
        self.make_submission(' APPLICANT@example.invalid ', name='Duplicate')
        campaign = self.campaign(status='ready')
        self.assertEqual(len(recipients(campaign)), 1)
        activate_campaign(campaign.pk)
        self.make_submission('later@example.invalid')
        activate_campaign(campaign.pk)
        self.assertEqual(campaign.messages.count(), 1)
        message = campaign.messages.get()
        self.assertEqual(message.recipient_email, 'applicant@example.invalid')
        self.assertNotIn('applicant@', message.event_key)
        self.assertIn('Example Applicant', message.text_content)
        self.assertEqual(message.status, 'pending')

    def test_filters_and_custom_applicants_are_event_scoped(self):
        approved = self.make_submission('approved@example.invalid')
        approved.status = 'approved'; approved.save()
        PaymentVerification.objects.create(submission=approved, status='verified')
        for filters, count in (({'statuses': ['approved']}, 1), ({'form_types': ['delegate']}, 2), ({'payment_status': 'unpaid'}, 1), ({'payment_status': 'verified'}, 1), ({'selection': 'custom', 'submission_ids': [str(approved.pk)]}, 1)):
            campaign = self.campaign(recipient_filter=filters)
            self.assertEqual(len(recipients(campaign)), count)
        bad = self.client.post('/api/admin/email/recipients/', {'event': self.event.pk, 'recipient_filter': {'selection': 'custom', 'submission_ids': []}}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.client.post('/api/admin/email/recipients/', {'event': self.event.pk, 'recipient_filter': {'emails': ['arbitrary@example.com']}}, format='json').status_code, 400)

    def test_schedule_pause_resume_cancel_and_send_confirmation(self):
        self.quiet()
        campaign = self.campaign()
        url = f'/api/admin/email/campaigns/{campaign.pk}/'
        self.assertEqual(self.client.post(url+'send/', {}, format='json').status_code, 400)
        result = self.client.post(url+'schedule/', {'confirm': True, 'scheduled_at': (timezone.now()+timedelta(hours=2)).isoformat()}, format='json')
        self.assertEqual(result.status_code, 202)
        activate_due()
        self.assertFalse(campaign.messages.exists())
        EmailCampaign.objects.filter(pk=campaign.pk).update(scheduled_at=timezone.now()-timedelta(seconds=1))
        activate_due()
        self.assertEqual(campaign.messages.count(), 1)
        self.assertEqual(self.client.post(url+'pause/', {}, format='json').status_code, 202)
        with patch('mailing.providers.requests.post') as send:
            process(10)
            send.assert_not_called()
        self.assertEqual(self.client.post(url+'resume/', {}, format='json').status_code, 202)
        self.assertEqual(self.client.post(url+'cancel/', {}, format='json').status_code, 202)
        self.assertEqual(campaign.messages.get().status, 'cancelled')
        self.assertEqual(self.client.patch(url, {'subject': 'Do not edit frozen jobs'}, format='json').status_code, 400)

    def test_daily_quota_and_transactional_reserve_prioritize_confirmations(self):
        campaign = self.campaign(status='ready'); activate_campaign(campaign.pk)
        with override_settings(EMAIL_DAILY_LIMIT=3, EMAIL_TRANSACTIONAL_RESERVE=2):
            quota = EmailDailyQuota.objects.create(day=quota_day(), used=1, bulk_used=1)
            with patch('mailing.providers.requests.post', return_value=self.accepted()) as send:
                result = process(10)
                self.assertEqual(result['processed'], 1)
                self.assertEqual(send.call_count, 1)
            self.job.refresh_from_db(); self.assertEqual(self.job.status, 'accepted')
            self.assertEqual(campaign.messages.get().status, 'pending')
            quota.refresh_from_db(); self.assertEqual(quota.used, 2)
            quota.used = 3; quota.save()
            with patch('mailing.providers.requests.post') as send:
                self.assertEqual(process(10)['processed'], 0)
                send.assert_not_called()
            quota.day -= timedelta(days=1); quota.save()
            with patch('mailing.providers.requests.post', return_value=self.accepted()):
                self.assertEqual(process(10)['processed'], 1)

    def test_rate_limits_retry_backoff_attempt_bounds_and_manual_retry(self):
        response = Mock(status_code=429, headers={'Retry-After': '20'})
        with patch('mailing.providers.requests.post', return_value=response):
            process(1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'retry')
        self.assertGreater(self.job.next_attempt_at, timezone.now()+timedelta(seconds=15))
        EmailMessage.objects.filter(pk=self.job.pk).update(next_attempt_at=timezone.now()-timedelta(seconds=1))
        with patch('mailing.providers.requests.post', return_value=response): process(1)
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'failed')
        self.assertTrue(self.job.retryable)
        self.assertEqual(self.client.post(f'/api/admin/email/messages/{self.job.pk}/retry/', {'confirm': True}, format='json').status_code, 200)
        with patch('mailing.providers.requests.post', return_value=self.accepted()): process(1)
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'accepted')
        self.assertEqual(list(self.job.attempts.values_list('number', flat=True)), [1, 2, 3])
        self.assertEqual(self.client.post(f'/api/admin/email/messages/{self.job.pk}/retry/', {'confirm': True}, format='json').status_code, 400)

    def test_uncertain_provider_outcomes_are_never_automatically_resent(self):
        with patch('mailing.providers.requests.post', side_effect=requests.ReadTimeout('sensitive provider text')) as send:
            process(1); process(1)
            self.assertEqual(send.call_count, 1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'unknown')
        self.assertNotIn('sensitive', self.job.last_error)
        self.assertEqual(self.client.post(f'/api/admin/email/messages/{self.job.pk}/retry/', {'confirm': True}, format='json').status_code, 400)
        result = self.client.post(f'/api/admin/email/messages/{self.job.pk}/resolve/', {'confirm': True, 'resolution': 'accepted', 'provider_message_id': '<confirmed@brevo.test>'}, format='json')
        self.assertEqual(result.status_code, 200)
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'accepted'); self.assertIsNone(self.job.delivered_at)

    def test_expired_worker_lease_becomes_unknown_and_dry_run_is_read_only(self):
        EmailMessage.objects.filter(pk=self.job.pk).update(status='sending', claimed_at=timezone.now()-timedelta(minutes=10))
        before = EmailDailyQuota.objects.count()
        self.assertTrue(process(2, dry_run=True)['dry_run'])
        self.assertEqual(EmailDailyQuota.objects.count(), before)
        with patch('mailing.providers.requests.post') as send:
            process(2)
            send.assert_not_called()
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'unknown')
        with override_settings(EMAIL_ENABLED=False):
            self.assertEqual(process()['processed'], 0)

    def test_provider_payload_one_recipient_no_documents_and_safe_failure_records(self):
        with patch('mailing.providers.requests.post', return_value=self.accepted()) as send:
            process(1)
            payload = send.call_args.kwargs['json']
            self.assertEqual(len(payload['to']), 1)
            self.assertNotIn('cc', payload); self.assertNotIn('bcc', payload); self.assertNotIn('attachment', payload)
            self.assertEqual(payload['headers']['idempotencyKey'], str(self.job.pk))
            self.assertEqual(send.call_args.kwargs['timeout'], (settings.EMAIL_CONNECT_TIMEOUT, settings.EMAIL_READ_TIMEOUT))
        self.job.refresh_from_db(); self.assertIsNone(self.job.delivered_at)
        EmailMessage.objects.filter(pk=self.job.pk).update(status='pending')
        failed = Mock(status_code=400)
        failed.json.return_value = {'code': 'invalid_parameter', 'message': 'secret-key and applicant PII'}
        with patch('mailing.providers.requests.post', return_value=failed): process(1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'failed'); self.assertFalse(self.job.retryable)
        self.assertNotIn('secret-key', str(list(self.job.attempts.values())))

    def test_templates_escape_values_sanitize_html_and_reject_code(self):
        subject, body, text = render('Hello {{full_name}}', '<p onclick="alert(1)">{{full_name}}</p><script>alert(1)</script><a href="javascript:alert(1)">link</a><img src="https://example.invalid/private">', 'Hello {{full_name}}', {'full_name': '<img src=x onerror=alert(1)>'})
        self.assertNotIn('<script', body); self.assertNotIn('onclick', body); self.assertNotIn('href="javascript', body); self.assertNotIn('<img', body)
        self.assertIn('&lt;img', body)
        for invalid in ('https://res.cloudinary.com/private-document', '{{unknown}}', '{{full_name|safe}}', '{% include "secrets" %}', '{{ request.user }}'):
            with self.assertRaises(Exception): validate_content('Subject', invalid, 'Text')
        preview = self.client.post('/api/admin/email/templates/preview/', {'subject': 'Subject', 'html_content': '<p>{{full_name}}</p>', 'text_content': '{{event_name}}'}, format='json')
        self.assertEqual(preview.status_code, 200)

    def test_webhook_authentication_deduplication_and_ordering(self):
        EmailMessage.objects.filter(pk=self.job.pk).update(status='accepted', provider_message_id='id@brevo', accepted_at=timezone.now())
        event = {'event': 'delivered', 'email': self.job.recipient_email, 'message-id': '<id@brevo>', 'ts_event': int(timezone.now().timestamp())}
        self.assertEqual(self.client.post('/api/webhooks/brevo/', event, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/webhooks/brevo/', event, format='json', HTTP_AUTHORIZATION='Bearer invalidé').status_code, 403)
        for _ in range(2):
            self.assertEqual(self.client.post('/api/webhooks/brevo/', event, format='json', HTTP_AUTHORIZATION='Bearer test-only-webhook').status_code, 200)
        self.assertEqual(EmailWebhookEvent.objects.count(), 1)
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'delivered')
        self.assertIsNotNone(self.job.delivered_at)
        earlier = {**event, 'event': 'deferred', 'ts_event': event['ts_event']-30}
        self.client.post('/api/webhooks/brevo/', earlier, format='json', HTTP_AUTHORIZATION='Bearer test-only-webhook')
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'delivered')
        mismatch = {**event, 'email': 'other@example.invalid'}
        self.assertEqual(self.client.post('/api/webhooks/brevo/', mismatch, format='json', HTTP_AUTHORIZATION='Bearer test-only-webhook').status_code, 400)

    def test_hard_bounces_suppress_future_jobs_and_early_webhooks_correlate(self):
        data = {'event': 'hard_bounce', 'email': self.job.recipient_email, 'message-id': 'early@brevo', 'X-Mailin-custom': f'munc-message:{self.job.pk}', 'ts_event': int(timezone.now().timestamp())}
        result = self.client.post('/api/webhooks/brevo/', data, format='json', HTTP_AUTHORIZATION='Bearer test-only-webhook')
        self.assertEqual(result.status_code, 200)
        self.assertTrue(EmailPreference.objects.get().suppressed)
        EmailMessage.objects.filter(pk=self.job.pk).update(status='pending')
        with patch('mailing.providers.requests.post') as send:
            process(1); send.assert_not_called()
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'skipped')

    def test_marketing_requires_explicit_consent_and_unsubscribe_is_safe(self):
        campaign = self.campaign(classification='marketing', status='ready')
        self.assertEqual(len(recipients(campaign)), 0)
        pref = EmailPreference.objects.create(email=self.submission.applicant_email, marketing_opt_in=True, consent_evidence='Explicit optional email consent')
        self.assertEqual(len(recipients(campaign)), 1)
        activate_campaign(campaign.pk)
        job = campaign.messages.get()
        self.assertIn('/email/unsubscribe/?token=', job.text_content)
        token = signing.dumps({'preference': pref.pk}, salt='munc-mail-unsubscribe')
        path = f'/api/email/unsubscribe/?token={token}'
        self.client.get(path)
        pref.refresh_from_db(); self.assertTrue(pref.marketing_opt_in)
        self.assertEqual(self.client.post(path, {}).status_code, 200)
        pref.refresh_from_db(); self.assertFalse(pref.marketing_opt_in)
        self.assertEqual(len(recipients(campaign)), 0)
        self.assertEqual(self.client.post('/api/email/unsubscribe/?token=invalid', {}).status_code, 400)
        self.quiet(); job.status = 'pending'; job.save()
        with patch('mailing.providers.requests.post') as send:
            process(1); send.assert_not_called()

    def test_role_permissions_cross_event_access_and_session_csrf(self):
        manager = get_user_model().objects.create_user('mail-manager', is_staff=True, email='manager@example.invalid')
        manager.groups.add(Group.objects.get(name='Event Admin'))
        reviewer = get_user_model().objects.create_user('mail-reviewer', is_staff=True)
        reviewer.groups.add(Group.objects.get(name='Reviewer'))
        other = Event.objects.create(title='Other event', slug='other-mail', event_type='conference', start_date=timezone.now())
        other_campaign = self.campaign(event=other)
        for user in (None, reviewer):
            self.client.force_authenticate(user)
            for path in ('overview/', 'templates/', 'campaigns/', 'messages/', 'configuration/'):
                self.assertEqual(self.client.get('/api/admin/email/'+path).status_code, 403)
        EventAssignment.objects.create(user=manager, event=self.event)
        self.client.force_authenticate(manager)
        self.assertEqual(self.client.get('/api/admin/email/overview/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/admin/email/campaigns/{other_campaign.pk}/').status_code, 404)
        self.assertEqual(self.client.post('/api/admin/email/recipients/', {'event': other.pk}, format='json').status_code, 403)
        global_template = EmailTemplate.objects.filter(event__isnull=True).first()
        self.assertEqual(self.client.patch(f'/api/admin/email/templates/{global_template.pk}/', {'subject': 'Forbidden'}, format='json').status_code, 404)
        self.assertNotIn('BREVO_API_KEY', str(self.client.get('/api/admin/email/configuration/').data))
        secure = APIClient(enforce_csrf_checks=True); secure.force_login(manager)
        self.assertEqual(secure.post('/api/admin/email/recipients/', {'event': self.event.pk}, format='json').status_code, 403)

    def test_test_email_is_admin_only_and_request_key_is_idempotent(self):
        campaign = self.campaign()
        key = str(uuid.uuid4())
        path = f'/api/admin/email/campaigns/{campaign.pk}/test/'
        for _ in range(2):
            self.assertEqual(self.client.post(path, {'request_key': key, 'recipient': 'arbitrary@example.com'}, format='json').status_code, 202)
        messages = EmailMessage.objects.filter(message_type='admin_test')
        self.assertEqual(messages.count(), 1)
        self.assertEqual(messages.get().recipient_email, self.root.email)
        self.assertEqual(messages.get().classification, 'operational')

    def test_queue_insertion_failure_is_reconciled_and_retention_preserves_keys(self):
        self.quiet()
        with patch('mailing.notifications.queue_notification', side_effect=DatabaseError('DB failure')):
            with self.captureOnCommitCallbacks(execute=True):
                submission = self.make_submission('recover@example.invalid')
        self.assertFalse(EmailMessage.objects.filter(submission=submission).exists())
        self.assertTrue(FormSubmission.objects.filter(pk=submission.pk).exists())
        reconcile()
        self.assertEqual(EmailMessage.objects.filter(submission=submission).count(), 1)
        campaign = self.campaign(status='ready'); activate_campaign(campaign.pk)
        EmailMessage.objects.update(status='delivered', updated_at=timezone.now()-timedelta(days=200))
        keys = set(EmailMessage.objects.values_list('event_key', flat=True))
        call_command('purge_email_history', stdout=StringIO())
        self.assertTrue(all(email == '' for email in EmailMessage.objects.values_list('recipient_email', flat=True)))
        self.assertEqual(keys, set(EmailMessage.objects.values_list('event_key', flat=True)))
        queue_notification('registration', self.submission.pk)
        self.assertEqual(EmailMessage.objects.filter(event_key=f'registration:{self.submission.pk}').count(), 1)

    def test_management_command_dry_run_does_not_send(self):
        output = StringIO()
        with patch('mailing.providers.requests.post') as send:
            call_command('process_email_queue', limit=3, dry_run=True, transactional_only=True, stdout=output)
            send.assert_not_called()
        self.assertIn('dry_run', output.getvalue())

    def test_failed_campaign_can_be_explicitly_retried_without_resending_accepted_jobs(self):
        self.quiet()
        campaign = self.campaign(status='ready'); activate_campaign(campaign.pk)
        response = Mock(status_code=429, headers={'Retry-After': '1'})
        with patch('mailing.providers.requests.post', return_value=response):
            process(1)
            campaign.messages.update(next_attempt_at=timezone.now()-timedelta(seconds=1))
            process(1)
        campaign.refresh_from_db(); self.assertEqual(campaign.status, 'completed')
        job = campaign.messages.get(); self.assertEqual(job.status, 'failed')
        result = self.client.post(f'/api/admin/email/messages/{job.pk}/retry/', {'confirm': True}, format='json')
        self.assertEqual(result.status_code, 200)
        campaign.refresh_from_db(); self.assertEqual(campaign.status, 'sending')
        with patch('mailing.providers.requests.post', return_value=self.accepted()) as send:
            process(5); self.assertEqual(send.call_count, 1)
        job.refresh_from_db(); self.assertEqual(job.status, 'accepted')

    def test_provider_classifies_connect_timeouts_and_ambiguous_responses_conservatively(self):
        self.job.sender_email = settings.DEFAULT_FROM_EMAIL
        with patch('mailing.providers.requests.post', side_effect=requests.ConnectTimeout):
            self.assertEqual(BrevoProvider().send(self.job).outcome, 'retry')
        for code, body in ((201, {}), (503, {}), (400, {'code': 'duplicate_parameter'})):
            response = Mock(status_code=code); response.json.return_value = body
            with patch('mailing.providers.requests.post', return_value=response):
                self.assertEqual(BrevoProvider().send(self.job).outcome, 'unknown')

    def test_template_crud_settings_and_paused_auto_notifications(self):
        data = {'name': 'Event confirmation override', 'template_key': 'registration_confirmation', 'event': self.event.pk,
            'subject': 'Received {{event_name}}', 'html_content': '<p>{{full_name}}</p>', 'text_content': 'Hello {{full_name}}', 'is_active': True}
        created = self.client.post('/api/admin/email/templates/', data, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        invalid = self.client.patch(f'/api/admin/email/templates/{created.data["id"]}/', {'text_content': '{{unknown}}'}, format='json')
        self.assertEqual(invalid.status_code, 400)
        duplicate = self.client.post('/api/admin/email/templates/', data, format='json')
        self.assertEqual(duplicate.status_code, 400)
        settings_url = f'/api/admin/email/settings/{self.event.pk}/'
        self.assertEqual(self.client.patch(settings_url, {'registration_enabled': False}, format='json').status_code, 200)
        with patch('mailing.providers.requests.post') as send:
            process(1); send.assert_not_called()
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'skipped')

    def test_database_failure_after_provider_acceptance_is_not_resent(self):
        with patch('mailing.providers.requests.post', return_value=self.accepted()) as send:
            with patch('mailing.queue.finish', side_effect=DatabaseError('Commit failed')):
                with self.assertRaises(DatabaseError): process(1)
            self.assertEqual(send.call_count, 1)
            self.job.refresh_from_db(); self.assertEqual(self.job.status, 'sending')
            EmailMessage.objects.filter(pk=self.job.pk).update(claimed_at=timezone.now()-timedelta(minutes=10))
            process(1)
            self.assertEqual(send.call_count, 1)
        self.job.refresh_from_db(); self.assertEqual(self.job.status, 'unknown')

    def test_campaign_snapshot_database_failure_rolls_back_and_repeats_safely(self):
        campaign = self.campaign(status='ready')
        with patch('mailing.campaigns.EmailMessage.objects.bulk_create', side_effect=DatabaseError('Snapshot write failed')):
            with self.assertRaises(DatabaseError): activate_campaign(campaign.pk)
        self.assertFalse(campaign.messages.exists())
        campaign.refresh_from_db(); self.assertIsNone(campaign.snapshot_at)
        activate_campaign(campaign.pk)
        self.assertEqual(campaign.messages.count(), 1)


@override_settings(**EMAIL_TEST)
class CommitTests(EmailSetup, TransactionTestCase):
    def test_rollback_never_queues_and_provider_failure_cannot_break_registration(self):
        before = EmailMessage.objects.count()
        with self.assertRaises(ValueError):
            with transaction.atomic():
                submit_application(self.form.pk, 'rolled-back@example.invalid', self.version.number, {'full_name': 'Rollback'})
                raise ValueError('Roll back')
        self.assertEqual(EmailMessage.objects.count(), before)
        with patch('mailing.providers.requests.post', side_effect=requests.ReadTimeout) as send:
            submission = submit_application(self.form.pk, 'committed@example.invalid', self.version.number, {'full_name': 'Committed'})
            self.assertTrue(FormSubmission.objects.filter(pk=submission.pk).exists())
            self.assertEqual(EmailMessage.objects.filter(submission=submission, message_type='registration_confirmation').count(), 1)
            send.assert_not_called()

    @skipUnless(connection.vendor == 'postgresql', 'Parallel row-lock verification requires PostgreSQL; SQLite is a local single-worker fallback.')
    def test_parallel_workers_claim_each_job_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import close_old_connections
        for index in range(10):
            row = self.make_submission(f'parallel{index}@example.invalid')
            queue_notification('registration', row.pk)
        def worker():
            close_old_connections(); claimed = []
            try:
                while True:
                    job, reason = claim()
                    if reason == 'rate': continue
                    if not job: break
                    claimed.append(job.pk)
                    finish(job.pk, SendResult('accepted', message_id=f'{job.pk}@test'))
                return claimed
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        ids = [pk for group in results for pk in group]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), EmailMessage.objects.count())
