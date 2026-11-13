from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import DatabaseError, close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient
from .models import RateLimitCounter
from .rate_limits import consume, database_now, selected_backend, RateLimitUnavailable


@override_settings(RATE_LIMIT_BACKEND='database', REDIS_URL='', DEBUG=False,
    SECURE_SSL_REDIRECT=False, CSRF_TRUSTED_ORIGINS=['https://club.example'],
    LOGIN_RATE_PER_MINUTE=100, LOGIN_RATE_PER_HOUR=1000, LOGIN_USERNAME_RATE_PER_15_MINUTES=100)
class DatabaseLoginTests(TestCase):
    def setUp(self):
        self.password = 'isolated-throttle-test-pass-712!'
        self.user = get_user_model().objects.create_superuser('throttle-admin', 'admin@example.invalid', self.password)
        self.client = APIClient(enforce_csrf_checks=True)
    def login(self, password=None, username='throttle-admin', ip='127.0.0.1'):
        token = self.client.get('/api/admin/auth/csrf/', secure=True).data['csrf_token']
        return self.client.post('/api/admin/auth/login/', {'username': username, 'password': self.password if password is None else password},
            format='json', secure=True, HTTP_ORIGIN='https://club.example', HTTP_X_CSRFTOKEN=token, REMOTE_ADDR=ip)
    def test_production_without_redis_logs_in_and_preserves_superuser(self):
        with override_settings(RATE_LIMIT_BACKEND='auto'):
            self.assertEqual(selected_backend(), 'database')
            response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.get('/api/admin/auth/me/', secure=True).data['authenticated'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_superuser)
        self.assertTrue(self.user.check_password(self.password))
        self.assertEqual(RateLimitCounter.objects.count(), 3)
    def test_invalid_password_is_generic_and_counts_attempts(self):
        response = self.login('wrong')
        self.assertEqual(response.status_code, 401)
        unknown = self.login('wrong', username='not-a-user')
        self.assertEqual(response.data, unknown.data)
        self.assertEqual(response.data['detail'], 'Invalid administrator credentials.')
        self.assertTrue(RateLimitCounter.objects.filter(attempts=2).exists())
    def test_ip_minute_hour_and_normalized_username_limits(self):
        for setting in ['LOGIN_RATE_PER_MINUTE', 'LOGIN_RATE_PER_HOUR']:
            RateLimitCounter.objects.all().delete()
            with override_settings(**{setting: 1}):
                self.assertEqual(self.login('wrong').status_code, 401)
                response = self.login('wrong')
                self.assertEqual(response.status_code, 429)
                self.assertGreaterEqual(int(response['Retry-After']), 1)
        RateLimitCounter.objects.all().delete()
        with override_settings(LOGIN_USERNAME_RATE_PER_15_MINUTES=1):
            self.assertEqual(self.login('wrong', ip='127.0.0.2').status_code, 401)
            self.assertEqual(self.login('wrong', username=' THROTTLE-ADMIN ', ip='127.0.0.3').status_code, 429)
    def test_csrf_remains_required_and_failure_reveals_no_database_error(self):
        response = self.client.post('/api/admin/auth/login/', {'username': 'throttle-admin', 'password': self.password}, format='json')
        self.assertEqual(response.status_code, 403)
        with patch('accounts.rate_limits.database_consume', side_effect=DatabaseError('private database password')):
            response = self.login()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['detail'], 'Administrator login is temporarily unavailable.')
        self.assertNotIn('private', str(response.data))
        self.assertNotIn('_auth_user_id', self.client.session)
    def test_quota_identity_data_is_hashed_and_counts_saturate(self):
        for _ in range(4):
            try: consume('private-person@example.invalid', 'login:username', 1, 900)
            except Throttled: pass
        counter = RateLimitCounter.objects.get()
        self.assertNotIn('private-person', counter.key)
        self.assertEqual(counter.attempts, 2)
    def test_period_boundary_creates_new_quota_and_cleanup_preserves_active(self):
        now = database_now()
        RateLimitCounter.objects.create(key='expired', scope='test', expires_at=now-timedelta(seconds=1))
        RateLimitCounter.objects.create(key='active', scope='test', expires_at=now+timedelta(hours=1))
        output = StringIO()
        call_command('cleanup_rate_limits', dry_run=True, stdout=output)
        self.assertTrue(RateLimitCounter.objects.filter(pk='expired').exists())
        call_command('cleanup_rate_limits', limit=1, stdout=StringIO())
        self.assertFalse(RateLimitCounter.objects.filter(pk='expired').exists())
        self.assertTrue(RateLimitCounter.objects.filter(pk='active').exists())
        with patch('accounts.rate_limits.database_epoch_sql', return_value='3600'):
            consume('test-person', 'login:test', 1, 60)
            with self.assertRaises(Throttled): consume('test-person', 'login:test', 1, 60)
        with patch('accounts.rate_limits.database_epoch_sql', return_value='3660'):
            consume('test-person', 'login:test', 1, 60)
        self.assertEqual(RateLimitCounter.objects.filter(scope='login:test').count(), 2)
    @override_settings(DEBUG=True, RATE_LIMIT_BACKEND='auto', REDIS_URL='redis://test-only',
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_optional_redis_selection_and_no_reset_on_redis_failure(self):
        self.assertEqual(selected_backend(), 'redis')
        cache.clear()
        consume('redis-person', 'login:username', 1, 900)
        with self.assertRaises(Throttled): consume('redis-person', 'login:username', 1, 900)
        with patch('accounts.rate_limits.cache.incr', side_effect=RuntimeError('private Redis URL')):
            with self.assertRaises(RateLimitUnavailable): consume('other', 'login:username', 1, 900)
        self.assertFalse(RateLimitCounter.objects.exists())
    def test_production_checks_accept_database_without_redis(self):
        from registrations.checks import submission_configuration
        with override_settings(SUBMISSION_STORAGE_PROVIDER='cloudinary', CLOUDINARY_CONFIG={'cloud_name': 'test', 'api_key': 'test', 'api_secret': 'test'}):
            codes = {error.id for error in submission_configuration(None)}
        self.assertNotIn('registrations.E001', codes)
        self.assertNotIn('registrations.E002', codes)
        if connection.vendor == 'postgresql': self.assertNotIn('registrations.E003', codes)
    def test_explicit_redis_without_configuration_fails_closed(self):
        with override_settings(RATE_LIMIT_BACKEND='redis', REDIS_URL=''):
            with self.assertRaises(RateLimitUnavailable): consume('identity', 'login:test', 1, 60)

    def test_database_failure_does_not_fall_back_to_memory(self):
        with patch('accounts.rate_limits.connection.cursor', side_effect=DatabaseError('private credentials')):
            with self.assertRaises(RateLimitUnavailable): consume('identity', 'login:test', 1, 60)
        self.assertFalse(RateLimitCounter.objects.exists())


@override_settings(RATE_LIMIT_BACKEND='database', REDIS_URL='', DEBUG=False)
class PostgreSQLQuotaConcurrencyTests(TransactionTestCase):
    def test_parallel_attempts_obey_exact_limit_including_first_insert_race(self):
        if connection.vendor != 'postgresql': self.skipTest('Requires PostgreSQL row-lock and UPSERT semantics.')
        barrier = Barrier(12)
        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                consume('concurrent-account', 'login:username', 5, 3600)
                return 'allowed'
            except Throttled:
                return 'limited'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(attempt, range(12)))
        self.assertEqual(results.count('allowed'), 5)
        self.assertEqual(results.count('limited'), 7)
        self.assertEqual(RateLimitCounter.objects.get().attempts, 6)
    def test_separate_connections_share_public_submission_quota(self):
        if connection.vendor != 'postgresql': self.skipTest('Requires PostgreSQL concurrent connections.')
        from registrations.throttles import consume_quota
        barrier = Barrier(8)
        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                consume_quota('public@example.invalid', 'email', 3, 3600)
                return True
            except Throttled:
                return False
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(attempt, range(8)))
        self.assertEqual(sum(results), 3)
