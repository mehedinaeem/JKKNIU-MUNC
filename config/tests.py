import os
import subprocess
import sys
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient


class HealthTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_health_is_small_json_without_database(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_write_methods_are_rejected(self):
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)('/api/health/').status_code, 405)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:5173'])
    def test_allowed_cors_origin_and_preflight(self):
        response = self.client.options('/api/health/', HTTP_ORIGIN='http://localhost:5173',
                                       HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:5173')
        self.assertNotIn('Access-Control-Allow-Credentials', response)

    def test_unknown_cors_origin_is_not_allowed(self):
        response = self.client.get('/api/health/', HTTP_ORIGIN='https://untrusted.example')
        self.assertNotIn('Access-Control-Allow-Origin', response)

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True)
    def test_proxy_https_and_http_redirect(self):
        self.assertEqual(self.client.get('/api/health/').status_code, 301)
        response = self.client.get('/api/health/', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_apps_and_timezone(self):
        for name in ('accounts', 'events', 'forms', 'registrations'):
            self.assertTrue(apps.is_installed(name))
        self.assertEqual(settings.TIME_ZONE, 'Asia/Dhaka')
        self.assertTrue(timezone.is_aware(timezone.now()))


class DatabaseTests(TestCase):
    def test_auth_database_roundtrip(self):
        user = get_user_model().objects.create_user(username='test-member', password='test-only-password')
        self.assertTrue(get_user_model().objects.get(pk=user.pk).check_password('test-only-password'))
        self.assertTrue(timezone.is_aware(user.date_joined))


class EnvironmentTests(SimpleTestCase):
    def run_settings(self, **overrides):
        env = os.environ.copy()
        for key in ('DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'DATABASE_URL', 'DATABASE_SSL_REQUIRE', 'USE_SQLITE'):
            env.pop(key, None)
        env.update(PYTHON_DOTENV_DISABLED='1', **overrides)
        return subprocess.run(
            [sys.executable, '-c', 'import config.settings as s; print(s.DATABASES["default"]["ENGINE"])'],
            cwd=Path(__file__).resolve().parent.parent, env=env, capture_output=True, text=True,
        )

    def test_local_sqlite_fallback(self):
        result = self.run_settings(DEBUG='True', SECRET_KEY='test-only-key')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('sqlite3', result.stdout)

    def test_production_requires_secret_hosts_and_postgres(self):
        cases = [
            {},
            {'SECRET_KEY': 'short'},
            {'SECRET_KEY': 'test-only-setting-value-' * 4},
            {'SECRET_KEY': 'test-only-setting-value-' * 4, 'ALLOWED_HOSTS': 'api.example.com'},
            {'DEBUG': 'True', 'SECRET_KEY': 'test-only-key', 'USE_SQLITE': 'False'},
            {'DEBUG': 'invalid', 'SECRET_KEY': 'test-only-key'},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertNotEqual(self.run_settings(**case).returncode, 0)

    def test_postgres_url_configuration_without_connecting(self):
        result = self.run_settings(
            SECRET_KEY='test-only-setting-value-' * 4,
            ALLOWED_HOSTS='api.example.com',
            DATABASE_URL='postgresql://test:test@localhost/test',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('postgresql', result.stdout)
