from accounts.models import RateLimitCounter
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import connection, transaction, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from mailing.models import EmailMessage
from .models import StudentIdentity, MembershipRole, MUNCMember, MembershipApplication, ActivationInvitation, VerifiedContact, MembershipAuditLog
from .crypto import unseal
from .services import create_member, issue_invitation, redeem, token_hash
from .verification import StudentVerificationService, VerificationUnavailable

PASSWORD = 'A!distinct-strong-passphrase793'
FIXTURE = {'20230001': {'full_name': 'Test Student', 'department': 'English', 'student_id': 'ST-0001', 'session': '2023-24'}}


@override_settings(DEBUG=True, MEMBERSHIP_VERIFICATION_PROVIDER='mock', MEMBERSHIP_ALLOW_MOCK=True,
    MEMBERSHIP_MOCK_STUDENTS=FIXTURE, PUBLIC_SITE_URL='http://localhost:5173', EMAIL_ENABLED=False)
class MembershipTests(TestCase):
    def setUp(self):
        cache.clear()
        RateLimitCounter.objects.all().delete()
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser('membership-admin', 'admin@example.invalid', PASSWORD)
        self.role, _ = MembershipRole.objects.get_or_create(name='General Member')
        self.identity = StudentVerificationService().verify('20230001')
    def application_payload(self, client=None):
        client = client or self.client
        checked = client.post('/api/membership/lookup/', {'registration_number': '20230001', 'consent': True}, format='json')
        self.assertEqual(checked.status_code, 200)
        return {'registration_number': '20230001', 'lookup_token': checked.data['lookup_token'],
            'identity_confirmed': True, 'is_existing_member': False,
            'motivation': 'I want to practise diplomacy and contribute.', 'consent': True,
            'contact_email': 'unverified@example.invalid'}
    def member(self, email=True):
        return create_member(self.identity, self.role, self.admin, 'In-person student card and email ownership independently confirmed', 'student@example.invalid' if email else '')
    def invitation(self, member, delivery='in_person', purpose='activation'):
        invitation, url = issue_invitation(member, self.admin, 'Independent in-person ownership confirmation', delivery, purpose)
        if not url:
            body = unseal(EmailMessage.objects.get(event_key=f'membership:invitation:{invitation.pk}').text_content)
            url = next(word for word in body.split() if '#token=' in word)
        return invitation, parse_qs(urlsplit(url).fragment)['token'][0]
    def activate(self, member):
        invitation, token = self.invitation(member)
        redeem(token, 'activation', PASSWORD)
        member.refresh_from_db(); member.user.refresh_from_db()
        return token
    def login(self):
        return self.client.post('/api/membership/login/', {'identifier': '20230001', 'password': PASSWORD}, format='json')
    def test_application_does_not_grant_account_and_deduplicates(self):
        payload = self.application_payload()
        self.assertEqual(self.client.post('/api/membership/apply/', payload, format='json').status_code, 202)
        self.assertEqual(self.client.post('/api/membership/apply/', payload, format='json').status_code, 202)
        self.assertEqual(MembershipApplication.objects.count(), 1)
        self.assertFalse(MUNCMember.objects.exists())
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(EmailMessage.objects.filter(message_type='membership_application_received').count(), 1)
        self.assertFalse(VerifiedContact.objects.exists())
    def test_unknown_student_lookup_uses_generic_error_without_record(self):
        response = self.client.post('/api/membership/lookup/', {'registration_number': 'unknown123', 'consent': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('full_name', response.data)
        self.assertFalse(MembershipApplication.objects.exists())
    def test_number_alone_cannot_activate_or_claim_identity(self):
        member = self.member()
        self.assertFalse(member.user.is_active)
        self.assertFalse(member.user.has_usable_password())
        response = self.client.post('/api/membership/activate/', {'registration_number': '20230001', 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.client.post('/api/admin/members/', {'identity': self.identity.pk}, format='json').status_code, 403)
    def test_activation_single_use_hash_only_no_staff(self):
        member = self.member()
        invitation, token = self.invitation(member)
        self.assertEqual(invitation.token_hash, token_hash(token))
        self.assertNotEqual(invitation.token_hash, token)
        self.assertGreaterEqual(len(token), 40)
        self.assertEqual(self.client.post('/api/membership/activate/', {'token': token, 'password': PASSWORD}, format='json').status_code, 200)
        self.assertEqual(self.client.post('/api/membership/activate/', {'token': token, 'password': PASSWORD}, format='json').status_code, 400)
        member.refresh_from_db(); member.user.refresh_from_db()
        self.assertEqual(member.status, 'active')
        self.assertTrue(member.user.check_password(PASSWORD))
        self.assertFalse(member.user.is_staff)
        self.assertFalse(member.user.is_superuser)
        self.assertEqual(EmailMessage.objects.filter(message_type='membership_activated').count(), 1)
        self.assertNotIn(token, str(list(MembershipAuditLog.objects.values('details'))))
    def test_expired_revoked_random_and_weak_tokens_fail(self):
        member = self.member()
        invitation, token = self.invitation(member)
        self.assertEqual(self.client.post('/api/membership/activate/', {'token': token, 'password': 'password'}, format='json').status_code, 400)
        invitation.expires_at = timezone.now()-timedelta(seconds=1); invitation.save()
        self.assertEqual(self.client.post('/api/membership/activate/', {'token': token, 'password': PASSWORD}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/membership/activate/', {'token': 'z'*43, 'password': PASSWORD}, format='json').status_code, 400)
    def test_invitation_reissue_revokes_prior_and_never_lists_raw_links(self):
        member = self.member()
        invitation, old = self.invitation(member)
        ActivationInvitation.objects.filter(pk=invitation.pk).update(created_at=timezone.now()-timedelta(minutes=2))
        newer, token = self.invitation(member)
        invitation.refresh_from_db(); self.assertIsNotNone(invitation.revoked_at)
        with self.assertRaises(Exception): redeem(old, 'activation', PASSWORD)
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/admin/membership-invitations/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(token, str(response.data)); self.assertNotIn('token_hash', str(response.data))
    def test_verified_email_required_manual_delivery_works_with_no_brevo(self):
        member = self.member(email=False)
        with self.assertRaises(Exception): self.invitation(member, 'email')
        invitation, token = self.invitation(member)
        self.assertFalse(EmailMessage.objects.filter(event_key=f'membership:invitation:{invitation.pk}').exists())
        self.activate_from_token(token)
    def activate_from_token(self, token):
        self.assertEqual(self.client.post('/api/membership/activate/', {'token': token, 'password': PASSWORD}, format='json').status_code, 200)
    def test_email_invitation_queued_without_provider_call(self):
        member = self.member()
        with patch('mailing.providers.BrevoProvider.send', side_effect=RuntimeError('offline')) as send:
            invitation, token = self.invitation(member, 'email')
            self.activate_from_token(token)
        send.assert_not_called()
        self.assertTrue(EmailMessage.objects.filter(message_type='membership_activated').exists())
    def test_login_profile_identity_readonly_and_other_members_private(self):
        member = self.member(); self.activate(member)
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get('/api/membership/me/').data['identity']['registration_number'], '20230001')
        self.assertEqual(self.client.patch('/api/membership/me/', {'biography': 'Member bio'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch('/api/membership/me/', {'registration_number': 'other'}, format='json').status_code, 400)
        self.assertEqual(self.client.get(f'/api/admin/members/{member.pk}/').status_code, 403)
        self.assertEqual(self.client.get('/api/admin/membership-applications/').status_code, 403)
    def test_suspension_removes_access_and_old_sessions_after_restore(self):
        member = self.member(); self.activate(member); self.login()
        staff = APIClient(); staff.force_authenticate(self.admin)
        self.assertEqual(staff.post(f'/api/admin/members/{member.pk}/suspend/', {'reason': 'Officer-reviewed suspension decision'}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/membership/me/').status_code, 403)
        self.assertEqual(staff.post(f'/api/admin/members/{member.pk}/reactivate/', {'reason': 'Officer-reviewed restoration decision'}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/membership/me/').status_code, 403)
        self.assertEqual(self.login().status_code, 200)
    def test_reset_generic_single_use_verified_contact_only(self):
        member = self.member(); self.activate(member)
        one = self.client.post('/api/membership/password-reset/request/', {'identifier': 'student@example.invalid'}, format='json')
        two = self.client.post('/api/membership/password-reset/request/', {'identifier': 'unknown@example.invalid'}, format='json')
        self.assertEqual(one.data, two.data)
        job = EmailMessage.objects.get(message_type='membership_password_reset')
        token = parse_qs(urlsplit(next(word for word in unseal(job.text_content).split() if '#token=' in word)).fragment)['token'][0]
        self.assertEqual(self.client.post('/api/membership/password-reset/confirm/', {'token': token, 'password': PASSWORD+'new'}, format='json').status_code, 200)
        self.assertEqual(self.client.post('/api/membership/password-reset/confirm/', {'token': token, 'password': PASSWORD+'new'}, format='json').status_code, 400)
    def test_email_change_requires_password_owner_and_link(self):
        member = self.member(); self.activate(member); self.login()
        self.assertEqual(self.client.post('/api/membership/change-email/', {'email': 'new@example.invalid', 'password': 'wrong'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/membership/change-email/', {'email': 'new@example.invalid', 'password': PASSWORD}, format='json').status_code, 200)
        self.assertEqual(member.verified_contacts.get(is_current=True).value, 'student@example.invalid')
        job = EmailMessage.objects.get(message_type='membership_email_verification')
        token = parse_qs(urlsplit(next(word for word in unseal(job.text_content).split() if '#token=' in word)).fragment)['token'][0]
        self.assertEqual(self.client.post('/api/membership/change-email/', {'token': token}, format='json').status_code, 200)
        self.assertEqual(member.verified_contacts.get(is_current=True).value, 'new@example.invalid')
    def test_csrf_enforced_for_public_login_activation_and_application(self):
        client = APIClient(enforce_csrf_checks=True)
        for path in ['login', 'activate', 'lookup', 'apply', 'logout', 'password-reset/request']:
            self.assertEqual(client.post(f'/api/membership/{path}/', {}, format='json').status_code, 403)
        token = client.get('/api/admin/auth/csrf/').data['csrf_token']
        response = client.post('/api/membership/login/', {'identifier': 'missing', 'password': PASSWORD}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 401)
    @override_settings(LOGIN_USERNAME_RATE_PER_15_MINUTES=5)
    def test_login_throttled(self):
        for _ in range(5): self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login().status_code, 429)
    def test_verification_disabled_and_mock_production_blocked(self):
        with override_settings(MEMBERSHIP_VERIFICATION_PROVIDER='disabled'):
            with self.assertRaises(VerificationUnavailable): StudentVerificationService().verify('20230001')
        with override_settings(DEBUG=False):
            with self.assertRaises(VerificationUnavailable): StudentVerificationService().verify('20230001')
        with patch('membership.verification.MockStudentProvider.verify', side_effect=TimeoutError):
            with self.assertRaises(VerificationUnavailable): StudentVerificationService().verify('20230001')
    def test_designated_permission_superuser_and_staff_retained(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/admin/members/').status_code, 200)
        officer = get_user_model().objects.create_user('officer', is_staff=True)
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.get('/api/admin/members/').status_code, 403)
        officer.user_permissions.add(Permission.objects.get(codename='manage_membership'))
        officer = get_user_model().objects.get(pk=officer.pk)
        self.client.force_authenticate(officer)
        self.assertEqual(self.client.get('/api/admin/members/').status_code, 200)
        officer.set_password(PASSWORD); officer.save()
        fresh = APIClient()
        response = fresh.post('/api/admin/auth/login/', {'username': 'officer', 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Membership Admin', response.data['administrator']['roles'])
        self.assertFalse(response.data['administrator']['all_events'])
        self.assertEqual(fresh.get('/api/admin/email/overview/').status_code, 403)
    def test_rollback_does_not_leave_account_or_invitation(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                member = self.member(); self.invitation(member, 'email'); raise RuntimeError('rollback')
        self.assertFalse(MUNCMember.objects.exists()); self.assertFalse(ActivationInvitation.objects.exists())
        self.assertFalse(EmailMessage.objects.filter(message_type='membership_invitation').exists())
    def test_required_consent_and_identity_no_independent_claim(self):
        self.assertEqual(self.client.post('/api/membership/apply/', {'registration_number': '20230001', 'motivation': 'I wish to contribute to the club.', 'consent': False}, format='json').status_code, 400)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post('/api/admin/members/', {'identity': self.identity.pk, 'role': self.role.pk}, format='json').status_code, 400)
    def test_queued_private_links_encrypted_and_provider_decrypts_only_for_transport(self):
        from mailing.providers import BrevoProvider
        member = self.member()
        invitation, token = self.invitation(member, 'email')
        job = EmailMessage.objects.get(event_key=f'membership:invitation:{invitation.pk}')
        self.assertNotIn(token, job.html_content)
        self.assertNotIn(token, job.text_content)
        self.assertIn(token, unseal(job.text_content))
        job.sender_email = 'sender@example.invalid'
        from unittest.mock import Mock
        response = Mock(status_code=201)
        response.json.return_value = {'messageId': '<membership-id>'}
        with override_settings(BREVO_API_KEY='mock-provider-key'):
            with patch('mailing.providers.requests.post', return_value=response) as post:
                result = BrevoProvider().send(job)
                self.assertEqual(result.outcome, 'accepted')
                self.assertIn(token, post.call_args.kwargs['json']['textContent'])
                self.assertTrue(job.text_content.startswith('munc-encrypted:v1:'))
        with override_settings(SECRET_KEY='different-server-key', SECRET_KEY_FALLBACKS=[]):
            with self.assertRaises(Exception): unseal(job.text_content)

    def test_photo_reencoding_private_access_and_bad_file(self):
        import io, tempfile
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        member = self.member(); self.activate(member); self.login()
        with tempfile.TemporaryDirectory() as directory, override_settings(SUBMISSION_STORAGE_PROVIDER='temporary', LOCAL_PRIVATE_UPLOAD_ROOT=directory):
            self.assertEqual(self.client.post('/api/membership/photo/', {'photo': SimpleUploadedFile('bad.jpg', b'not-an-image', content_type='image/jpeg')}, format='multipart').status_code, 400)
            output = io.BytesIO(); Image.new('RGB', (20, 20), 'navy').save(output, format='PNG')
            result = self.client.post('/api/membership/photo/', {'photo': SimpleUploadedFile('safe.png', output.getvalue(), content_type='image/png')}, format='multipart')
            self.assertEqual(result.status_code, 200)
            response = self.client.get('/api/membership/photo/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertEqual(APIClient().get('/api/membership/photo/').status_code, 403)
            self.assertNotIn('provider', str(result.data))

    def test_admin_review_create_role_and_formula_safe_export(self):
        self.client.force_authenticate(self.admin)
        application = MembershipApplication.objects.create(student_identity=self.identity, motivation='Contributing to university diplomacy.', contact_email='untrusted@example.invalid')
        response = self.client.post(f'/api/admin/membership-applications/{application.pk}/approve/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MUNCMember.objects.exists())
        self.assertFalse(VerifiedContact.objects.exists())
        response = self.client.post('/api/admin/members/', {'identity': self.identity.pk, 'role': self.role.pk, 'identity_evidence': 'Independently identified student in person.'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.identity.full_name = '=UNSAFE()'; self.identity.save()
        result = self.client.get('/api/admin/members/export/')
        self.assertEqual(result.status_code, 200)
        self.assertIn("'=UNSAFE()", result.content.decode())
        self.assertNotIn('untrusted@example.invalid', result.content.decode())

    def test_password_change_invalidates_recovery_tokens(self):
        member = self.member(); self.activate(member); self.login()
        invitation, token = self.invitation(member, purpose='reset')
        self.assertEqual(self.client.post('/api/membership/change-password/', {'old_password': PASSWORD, 'password': PASSWORD+'changed'}, format='json').status_code, 200)
        invitation.refresh_from_db(); self.assertIsNotNone(invitation.revoked_at)
        self.assertEqual(self.client.get('/api/membership/me/').status_code, 200)
        with self.assertRaises(Exception): redeem(token, 'reset', PASSWORD)

    def test_wrong_member_cannot_redeem_email_change(self):
        member = self.member(); self.activate(member)
        invitation, _ = issue_invitation(member, member.user, 'Password-confirmed change', purpose='email', target_email='new@example.invalid')
        job = EmailMessage.objects.get(event_key=f'membership:invitation:{invitation.pk}')
        token = parse_qs(urlsplit(next(word for word in unseal(job.text_content).split() if '#token=' in word)).fragment)['token'][0]
        with self.assertRaises(Exception): redeem(token, 'email', owner=self.admin)
        invitation.refresh_from_db(); self.assertIsNone(invitation.used_at)

    def test_existing_member_choice_skips_motivation_but_grants_no_access(self):
        payload = self.application_payload()
        payload.update(is_existing_member=True, motivation='', experience='No longer applicable hidden answer')
        self.assertEqual(self.client.post('/api/membership/apply/', payload, format='json').status_code, 202)
        application = MembershipApplication.objects.get()
        self.assertTrue(application.is_existing_member)
        self.assertEqual(application.motivation, '')
        self.assertEqual(application.experience, '')
        self.assertIsNotNone(application.identity_confirmed_at)
        self.assertFalse(MUNCMember.objects.exists())
        self.assertEqual(self.login().status_code, 401)

    def test_email_confirmation_and_new_member_motivation_required(self):
        payload = self.application_payload()
        for field, value in [('contact_email', ''), ('identity_confirmed', False), ('motivation', ''), ('is_existing_member', None)]:
            invalid = payload | {field: value}
            response = self.client.post('/api/membership/apply/', invalid, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.data)
        self.assertFalse(MembershipApplication.objects.exists())

    def test_student_check_bound_to_browser_number_and_expiry(self):
        from django.core import signing
        from .views import LOOKUP_SALT
        payload = self.application_payload()
        stranger = APIClient()
        self.assertEqual(stranger.post('/api/membership/apply/', payload, format='json').status_code, 400)
        changed = payload | {'registration_number': 'OTHER-001'}
        self.assertEqual(self.client.post('/api/membership/apply/', changed, format='json').status_code, 400)
        data = signing.loads(payload['lookup_token'], salt=LOOKUP_SALT)
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp()-601):
            expired = signing.dumps(data, salt=LOOKUP_SALT)
        self.assertEqual(self.client.post('/api/membership/apply/', payload | {'lookup_token': expired}, format='json').status_code, 400)
        self.assertFalse(MembershipApplication.objects.exists())

    def test_public_preview_minimizes_identity_and_has_no_contact_or_account_status(self):
        response = self.client.post('/api/membership/lookup/', {'registration_number': '20230001', 'consent': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['student']['full_name'], 'Test Student')
        self.assertEqual(response.data['student']['department'], 'English')
        self.assertNotEqual(response.data['student']['student_id'], self.identity.student_id)
        self.assertNotIn('email', str(response.data['student']))
        self.assertNotIn('is_existing_member', response.data)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_expired_email_invitation_not_claimed(self):
        from mailing.queue import claim
        member = self.member(); invitation, _ = self.invitation(member, 'email')
        ActivationInvitation.objects.filter(pk=invitation.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        message, reason = claim()
        self.assertIsNone(message); self.assertEqual(reason, 'skipped')
        job = EmailMessage.objects.get(event_key=f'membership:invitation:{invitation.pk}')
        self.assertFalse(job.text_content)


class PostgreSQLActivationConcurrencyTests(TransactionTestCase):
    def test_parallel_activation_single_redemption(self):
        if connection.vendor != 'postgresql': self.skipTest('Requires a dedicated PostgreSQL test database for row locks.')
        from concurrent.futures import ThreadPoolExecutor
        identity = StudentIdentity.objects.create(registration_number='CONCURRENT1', full_name='Concurrent Student', department='Test', verification_source='authorized-test')
        role, _ = MembershipRole.objects.get_or_create(name='General Member')
        admin = get_user_model().objects.create_superuser('concurrent-admin', 'admin@example.invalid', PASSWORD)
        member = create_member(identity, role, admin, 'Independently confirmed in person')
        _, url = issue_invitation(member, admin, 'Independently confirmed in person', 'in_person')
        token = parse_qs(urlsplit(url).fragment)['token'][0]
        def run():
            close_old_connections()
            try:
                redeem(token, 'activation', PASSWORD)
                return True
            except Exception:
                return False
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor: results = list(executor.map(lambda _: run(), range(2)))
        self.assertEqual(sum(results), 1)
