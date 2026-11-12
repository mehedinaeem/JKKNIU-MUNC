from datetime import timedelta
from io import BytesIO, StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import EventAssignment
from accounts.roles import SUPER_ADMIN, EVENT_ADMIN, REVIEWER, setup_roles
from events.models import Event
from forms.models import RegistrationForm, FormField
from forms.services import publish_form
from registrations.models import FormSubmission, SubmissionFile, SubmissionStatusChange


@override_settings(DEBUG=True, LOGIN_RATE_PER_MINUTE=100, LOGIN_RATE_PER_HOUR=1000,
                   LOGIN_USERNAME_RATE_PER_15_MINUTES=100)
class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        setup_roles()
        cls.password = 'test-only-correct-password-592!'
        cls.superuser = get_user_model().objects.create_superuser('root-admin', 'root@example.com', cls.password)
        cls.manager = get_user_model().objects.create_user('manager-login', password=cls.password, is_staff=True)
        cls.manager.groups.add(Group.objects.get(name=EVENT_ADMIN))
        cls.reviewer = get_user_model().objects.create_user('reviewer-login', password=cls.password, is_staff=True)
        cls.reviewer.groups.add(Group.objects.get(name=REVIEWER))
        cls.staff = get_user_model().objects.create_user('staff-no-role', password=cls.password, is_staff=True)
        cls.nonstaff = get_user_model().objects.create_user('not-staff', password=cls.password)
        cls.nonstaff.groups.add(Group.objects.get(name=EVENT_ADMIN))
        cls.inactive = get_user_model().objects.create_user('inactive-login', password=cls.password, is_staff=True, is_active=False)
        cls.inactive.groups.add(Group.objects.get(name=REVIEWER))

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        response = self.client.get('/api/admin/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        return response.data['csrf_token']

    def login(self, user=None, token=None, password=None, **headers):
        return self.client.post('/api/admin/auth/login/', {
            'username': (user or self.manager).username,
            'password': self.password if password is None else password,
        }, format='json', HTTP_X_CSRFTOKEN=token or self.csrf(), **headers)

    def test_anonymous_status_and_csrf_cookie(self):
        response = self.client.get('/api/admin/auth/me/')
        self.assertEqual(response.data, {'authenticated': False, 'administrator': None})
        self.csrf()
        cookie = self.client.cookies['jkkniu_csrf']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')

    def test_login_for_each_role_and_logout_invalidates_session(self):
        for user, role in ((self.superuser, SUPER_ADMIN), (self.manager, EVENT_ADMIN), (self.reviewer, REVIEWER)):
            self.client = APIClient(enforce_csrf_checks=True)
            response = self.login(user)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertIn(role, response.data['administrator']['roles'])
            self.assertNotIn('password', response.data)
            self.assertNotIn('sessionid', response.data)
            self.assertTrue(self.client.cookies['jkkniu_admin_session']['httponly'])
            current = self.client.get('/api/admin/auth/me/')
            self.assertTrue(current.data['authenticated'])
            self.assertEqual(self.client.post('/api/admin/auth/logout/', {}, format='json').status_code, 403)
            response = self.client.post('/api/admin/auth/logout/', {}, format='json',
                HTTP_X_CSRFTOKEN=response.data['csrf_token'])
            self.assertEqual(response.status_code, 204, response.content)
            self.assertFalse(self.client.get('/api/admin/auth/me/').data['authenticated'])
            self.assertEqual(self.client.get('/api/admin/events/').status_code, 403)

    def test_login_needs_csrf_and_rejects_wrong_origin(self):
        response = self.client.post('/api/admin/auth/login/',
            {'username': self.manager.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('CSRF', response.json()['detail'])
        response = self.login(HTTP_ORIGIN='https://untrusted.example')
        self.assertEqual(response.status_code, 403)

    def test_trusted_local_origin_login_and_credentialed_cors(self):
        response = self.login(HTTP_ORIGIN='http://localhost:5173')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:5173')
        self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')

    def test_bad_credentials_inactive_and_nonadministrators_share_generic_error(self):
        results = []
        for user in (self.manager, self.staff, self.nonstaff, self.inactive):
            response = self.login(user, password='incorrect' if user == self.manager else self.password)
            self.assertEqual(response.status_code, 401, response.content)
            results.append(response.data)
        self.assertTrue(all(result == results[0] for result in results))
        self.assertFalse(self.client.get('/api/admin/auth/me/').data['authenticated'])

    def test_session_and_csrf_rotate_on_login_and_old_token_fails(self):
        first = self.login()
        session_key = self.client.cookies['jkkniu_admin_session'].value
        old_token = first.data['csrf_token']
        second = self.login(self.reviewer, token=old_token)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(session_key, self.client.cookies['jkkniu_admin_session'].value)
        response = self.client.post('/api/admin/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=old_token)
        self.assertEqual(response.status_code, 403)

    def test_role_revocation_and_disabled_accounts_invalidate_admin_access(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.manager.groups.clear()
        self.assertFalse(self.client.get('/api/admin/auth/me/').data['authenticated'])
        self.assertEqual(self.client.get('/api/admin/events/').status_code, 403)
        response = self.login(self.reviewer)
        self.assertEqual(response.status_code, 200)
        get_user_model().objects.filter(pk=self.reviewer.pk).update(is_active=False)
        self.assertFalse(self.client.get('/api/admin/auth/me/').data['authenticated'])

    def test_login_and_logout_reject_get(self):
        self.assertEqual(self.client.get('/api/admin/auth/login/').status_code, 405)
        self.assertEqual(self.client.get('/api/admin/auth/logout/').status_code, 405)

    def test_ip_username_and_fallback_login_limits(self):
        with override_settings(LOGIN_RATE_PER_MINUTE=1):
            self.assertEqual(self.login(password='wrong').status_code, 401)
            response = self.login(password='wrong')
            self.assertEqual(response.status_code, 429)
            self.assertIn('Retry-After', response)
        cache.clear()
        with override_settings(LOGIN_USERNAME_RATE_PER_15_MINUTES=1):
            self.assertEqual(self.login(password='wrong', REMOTE_ADDR='127.0.0.2').status_code, 401)
            self.assertEqual(self.login(password='wrong', REMOTE_ADDR='127.0.0.3').status_code, 429)
        cache.clear()
        with override_settings(LOGIN_RATE_PER_MINUTE=1):
            self.login(password='wrong')
            response = self.client.post('/admin/login/', {'username': self.manager.username, 'password': 'wrong'},
                HTTP_X_CSRFTOKEN=self.csrf())
            self.assertEqual(response.status_code, 429)

    def test_rate_limit_cache_failure_is_generic(self):
        token = self.csrf()
        with patch('accounts.throttles.cache.incr', side_effect=RuntimeError('private cache connection')):
            response = self.login(token=token)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private cache', str(response.data))

    def test_fallback_login_rejects_staff_without_role(self):
        self.client.get('/admin/login/')
        response = self.client.post('/admin/login/', {'username': self.staff.username, 'password': self.password,
            'csrfmiddlewaretoken': self.client.cookies['jkkniu_csrf'].value})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class RoleAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        setup_roles()
        cls.superuser = get_user_model().objects.create_superuser('scope-root', 'root@example.com', 'test-only-password')
        cls.supergroup = get_user_model().objects.create_user('scope-super-group', is_staff=True)
        cls.supergroup.groups.add(Group.objects.get(name=SUPER_ADMIN))
        cls.manager = get_user_model().objects.create_user('scope-manager', is_staff=True)
        cls.manager.groups.add(Group.objects.get(name=EVENT_ADMIN))
        cls.reviewer = get_user_model().objects.create_user('scope-reviewer', is_staff=True)
        cls.reviewer.groups.add(Group.objects.get(name=REVIEWER))
        cls.staff = get_user_model().objects.create_user('scope-plain-staff', is_staff=True)
        cls.events, cls.forms, cls.submissions, cls.files = [], [], [], []
        for i in range(2):
            event = Event.objects.create(title=f'Event {i}', slug=f'event-{i}', event_type='custom',
                status='published', start_date=timezone.now() + timedelta(days=30))
            form = RegistrationForm.objects.create(event=event, title=f'Form {i}', slug=f'form-{i}', form_type='custom')
            FormField.objects.create(form=form, key='name', label='Name', field_type='short_text')
            version = publish_form(form.pk)
            submission = FormSubmission.objects.create(event=event, registration_form=form, form_version=version,
                applicant_email=f'private{i}@example.com', answers={'name': f'Private applicant {i}'})
            upload = SubmissionFile.objects.create(submission=submission, field_key='document', storage_provider='temporary',
                provider_file_id=f'applications/{str(i)*32}.pdf', original_filename='private.pdf', content_type='application/pdf', file_size=3)
            cls.events.append(event)
            cls.forms.append(form)
            cls.submissions.append(submission)
            cls.files.append(upload)
        for user in (cls.manager, cls.reviewer):
            EventAssignment.objects.create(user=user, event=cls.events[0])

    def setUp(self):
        self.client = APIClient()

    def use(self, user):
        self.client.force_authenticate(user)

    def test_staff_flag_and_assignments_without_roles_do_not_grant_access(self):
        EventAssignment.objects.create(user=self.staff, event=self.events[0])
        self.staff.user_permissions.set(Permission.objects.all())
        self.use(self.staff)
        for url in ('/api/admin/events/', '/api/admin/submissions/', f'/api/admin/forms/{self.forms[0].pk}/'):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_superuser_and_super_admin_group_have_all_event_access(self):
        for user in (self.superuser, self.supergroup):
            self.use(user)
            self.assertEqual(self.client.get('/api/admin/events/').data['count'], 2)
            self.assertEqual(self.client.get('/api/admin/submissions/').data['count'], 2)
            self.assertEqual(self.client.patch(f'/api/admin/events/{self.events[1].pk}/',
                {'venue': 'Updated'}, format='json').status_code, 200)
            self.assertEqual(self.client.get(f'/api/admin/forms/{self.forms[1].pk}/').status_code, 200)

    def test_event_admin_can_manage_only_assigned_events_and_forms(self):
        self.use(self.manager)
        self.assertEqual(self.client.get('/api/admin/events/').data['count'], 1)
        self.assertEqual(self.client.patch(f'/api/admin/events/{self.events[0].pk}/', {'venue': 'Assigned'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/admin/events/{self.events[1].pk}/', {'venue': 'Denied'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/admin/events/{self.events[1].pk}/').status_code, 404)
        self.assertEqual(self.client.post('/api/admin/events/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/admin/events/{self.events[0].pk}/', {'organizer': self.manager.pk}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/admin/forms/{self.forms[0].pk}/', {'title': 'Managed'}, format='json').status_code, 200)
        for suffix in ('', 'preview/', 'publish/', 'duplicate/'):
            url = f'/api/admin/forms/{self.forms[1].pk}/' + suffix
            response = self.client.get(url) if suffix in ('', 'preview/') else self.client.post(url, {}, format='json')
            self.assertEqual(response.status_code, 404, url)
        payload = {'event': self.events[1].pk, 'title': 'Denied', 'slug': 'denied', 'form_type': 'custom'}
        self.assertEqual(self.client.post('/api/admin/forms/', payload, format='json').status_code, 403)
        payload.update(event=self.events[0].pk, slug='allowed')
        self.assertEqual(self.client.post('/api/admin/forms/', payload, format='json').status_code, 201)
        self.assertEqual(self.client.post(f'/api/admin/forms/{self.forms[0].pk}/publish/').status_code, 201)

    def test_reviewer_reads_and_reviews_only_assigned_applications(self):
        for user in (self.manager, self.reviewer):
            self.use(user)
            listed = self.client.get('/api/admin/submissions/')
            self.assertEqual(listed.data['count'], 1)
            self.assertEqual(listed.data['results'][0]['id'], str(self.submissions[0].pk))
            self.assertEqual(self.client.get(f'/api/admin/submissions/?event={self.events[1].pk}').data['count'], 0)
            own = self.client.get(f'/api/admin/submissions/{self.submissions[0].pk}/')
            self.assertEqual(own.status_code, 200)
            self.assertIn('form_schema', own.data)
            self.assertEqual(self.client.get(f'/api/admin/submissions/{self.submissions[1].pk}/').status_code, 404)
            self.assertEqual(self.client.patch(f'/api/admin/submissions/{self.submissions[1].pk}/status/',
                {'status': 'approved'}, format='json').status_code, 404)
            self.assertEqual(self.client.patch(f'/api/admin/submissions/{self.submissions[0].pk}/status/',
                {'status': 'under_review'}, format='json').status_code, 200)
        self.assertEqual(SubmissionStatusChange.objects.count(), 1)

    def test_reviewer_cannot_manage_events_or_forms_or_escalate_role(self):
        self.reviewer.user_permissions.set(Permission.objects.all())
        self.use(self.reviewer)
        self.assertEqual(self.client.get('/api/admin/events/').data['count'], 1)
        self.assertEqual(self.client.patch(f'/api/admin/events/{self.events[0].pk}/', {'venue': 'Denied'}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/admin/forms/{self.forms[0].pk}/', {'title': 'Denied'}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/admin/forms/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/admin/forms/{self.forms[0].pk}/publish/').status_code, 403)

    def test_files_require_assignment_before_provider_access(self):
        for user in (self.manager, self.reviewer):
            self.use(user)
            with patch('registrations.views.get_provider') as provider:
                self.assertEqual(self.client.get(f'/api/submission-files/{self.files[1].pk}/').status_code, 403)
                provider.assert_not_called()
            provider = Mock()
            provider.open.return_value = BytesIO(b'pdf')
            with patch('registrations.views.get_provider', return_value=provider):
                response = self.client.get(f'/api/submission-files/{self.files[0].pk}/')
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_assignment_revocation_takes_effect(self):
        self.use(self.manager)
        EventAssignment.objects.filter(user=self.manager).delete()
        self.assertEqual(self.client.get('/api/admin/events/').data['count'], 0)
        self.assertEqual(self.client.get('/api/admin/submissions/').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/admin/forms/{self.forms[0].pk}/').status_code, 404)

    def test_fallback_admin_scopes_lists_objects_and_foreign_key_choices(self):
        for user in (self.manager, self.reviewer):
            self.client = APIClient()
            self.client.force_login(user)
            response = self.client.get('/admin/events/event/')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.events[0].title)
            self.assertNotContains(response, self.events[1].title)
            response = self.client.get('/admin/registrations/formsubmission/')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.submissions[0].reference_number)
            self.assertNotContains(response, self.submissions[1].reference_number)
            response = self.client.get(f'/admin/registrations/formsubmission/{self.submissions[1].pk}/change/')
            self.assertIn(response.status_code, (302, 404))
            for path in ('auth/user', 'auth/group', 'accounts/eventassignment'):
                self.assertEqual(self.client.get(f'/admin/{path}/').status_code, 403)
        self.client.force_login(self.manager)
        response = self.client.get('/admin/club_forms/registrationform/add/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['adminform'].form.fields['event'].queryset), [self.events[0]])

    def test_fallback_status_review_is_scoped_and_audited(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(f'/admin/registrations/formsubmission/{self.submissions[0].pk}/change/',
                                   {'status': 'shortlisted', '_save': 'Save',
                                    'reviewer_notes-TOTAL_FORMS': '0', 'reviewer_notes-INITIAL_FORMS': '0',
                                    'status_changes-TOTAL_FORMS': '0', 'status_changes-INITIAL_FORMS': '0'})
        self.assertEqual(response.status_code, 302, response.content)
        self.submissions[0].refresh_from_db()
        self.assertEqual(self.submissions[0].status, 'shortlisted')
        self.assertEqual(SubmissionStatusChange.objects.get().changed_by_id, self.reviewer.pk)

    def test_only_super_admin_can_manage_accounts_groups_and_assignments(self):
        self.client.force_login(self.supergroup)
        for path in ('auth/user', 'auth/group', 'accounts/eventassignment'):
            self.assertEqual(self.client.get(f'/admin/{path}/').status_code, 200)
        self.reviewer.user_permissions.set(Permission.objects.all())
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 403)

    def test_form_list_includes_drafts_and_is_scoped(self):
        self.forms[0].status = 'draft'
        self.forms[0].save()
        self.use(self.manager)
        response = self.client.get('/api/admin/forms/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'draft')
        self.assertEqual(response.data['results'][0]['field_count'], 1)
        self.assertNotIn('fields', response.data['results'][0])
        self.assertEqual(self.client.get(f'/api/admin/forms/?event={self.events[1].pk}').data['count'], 0)
        self.assertEqual(self.client.get('/api/admin/forms/?event=invalid').status_code, 400)
        self.use(self.reviewer)
        self.assertEqual(self.client.get('/api/admin/forms/').status_code, 403)
        self.use(self.superuser)
        self.assertEqual(self.client.get('/api/admin/forms/').data['count'], 2)

    def test_role_setup_is_idempotent_and_does_not_assign_users(self):
        call_command('setup_admin_roles', stdout=StringIO())
        call_command('setup_admin_roles', stdout=StringIO())
        self.assertEqual(Group.objects.filter(name__in=[SUPER_ADMIN, EVENT_ADMIN, REVIEWER]).count(), 3)
        self.assertEqual(self.staff.groups.count(), 0)
        self.assertFalse(Group.objects.get(name=REVIEWER).permissions.filter(codename='change_event').exists())


from django.test import SimpleTestCase


class CookieConfigurationTests(SimpleTestCase):
    def settings_result(self, **changes):
        import json
        import os
        from pathlib import Path
        import subprocess
        import sys
        from dotenv import dotenv_values
        env = os.environ.copy()
        for key in dotenv_values(Path(__file__).resolve().parent.parent / '.env.example'):
            env.pop(key, None)
        env.update(PYTHON_DOTENV_DISABLED='1', DEBUG='False', SECRET_KEY='test-only-cookie-config-value-' * 4,
                   ALLOWED_HOSTS='api.example.com', DATABASE_URL='postgresql://test:test@localhost/test',
                   SUBMISSION_STORAGE_PROVIDER='cloudinary', AUTH_COOKIE_MODE='proxy')
        env.update(changes)
        return subprocess.run([sys.executable, '-c',
            'import json; import config.settings as s; print(json.dumps([s.SESSION_COOKIE_SAMESITE, s.CSRF_COOKIE_SAMESITE, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SESSION_COOKIE_HTTPONLY, s.CORS_ALLOW_CREDENTIALS]))'],
            cwd=Path(__file__).resolve().parent.parent, env=env, capture_output=True, text=True)

    def test_proxy_mode_uses_secure_first_party_cookies_in_production(self):
        import json
        result = self.settings_result()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ['Lax', 'Lax', True, True, True, False])

    def test_cross_site_mode_is_explicit_and_secure(self):
        import json
        config = {'AUTH_COOKIE_MODE': 'cross_site', 'CORS_ALLOWED_ORIGINS': 'https://console.example.com',
                  'CSRF_TRUSTED_ORIGINS': 'https://console.example.com'}
        result = self.settings_result(**config)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ['None', 'None', True, True, True, True])
        for changes in ({'DEBUG': 'True'}, {'CSRF_TRUSTED_ORIGINS': ''},
                        {'CORS_ALLOWED_ORIGINS': 'http://console.example.com'}, {'CORS_ALLOW_CREDENTIALS': 'False'},
                        {'CORS_ALLOWED_ORIGINS': 'https://*.example.com'},
                        {'CSRF_TRUSTED_ORIGINS': 'https://console.example.com,https://*.example.com'}):
            with self.subTest(changes=changes):
                result = self.settings_result(**{**config, **changes})
                self.assertNotEqual(result.returncode, 0)
