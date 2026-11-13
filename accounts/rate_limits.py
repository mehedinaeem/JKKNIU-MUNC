"""Shared fail-closed quotas. PostgreSQL UPSERT serializes claims for a bucket.

No Python read/modify/write or process-local production fallback. Window time is
read from the database in the same SQL statement that consumes the attempt.
"""
import math
import time
from datetime import datetime, timezone
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import Throttled
from .models import RateLimitCounter


class RateLimitUnavailable(Exception):
    pass


def selected_backend():
    mode = settings.RATE_LIMIT_BACKEND
    if mode == 'auto': return 'redis' if settings.REDIS_URL else 'database'
    return mode


def database_epoch_sql():
    if connection.vendor == 'postgresql':
        return 'CAST(FLOOR(EXTRACT(EPOCH FROM statement_timestamp())) AS BIGINT)'
    if connection.vendor == 'sqlite':
        return "CAST(strftime('%%s', 'now') AS BIGINT)"
    raise RateLimitUnavailable()


def database_now():
    with connection.cursor() as cursor:
        # An empty parameter list makes Django unescape SQLite's literal percent.
        cursor.execute('SELECT ' + database_epoch_sql(), [])
        return datetime.fromtimestamp(int(cursor.fetchone()[0]), tz=timezone.utc)


def database_consume(identity, namespace, limit, period):
    table = connection.ops.quote_name(RateLimitCounter._meta.db_table)
    digest = salted_hmac('shared-rate-limit', identity, algorithm='sha256').hexdigest()
    epoch = database_epoch_sql()
    expiry = 'to_timestamp((slot + 1) * %s + %s)' if connection.vendor == 'postgresql' else "strftime('%%Y-%%m-%%d %%H:%%M:%%f', (slot + 1) * %s + %s, 'unixepoch')"
    # WHERE true avoids SQLite's INSERT SELECT / ON CONFLICT parsing ambiguity.
    sql = f'''WITH clock AS (SELECT {epoch} AS ts),
        bucket AS (SELECT CAST(ts / %s AS BIGINT) AS slot FROM clock)
        INSERT INTO {table} (key, scope, attempts, expires_at)
        SELECT %s || CAST(slot AS TEXT) || %s, %s, 1, {expiry}
        FROM bucket WHERE true
        ON CONFLICT (key) DO UPDATE SET attempts =
            CASE WHEN {table}.attempts < %s THEN {table}.attempts + 1 ELSE {table}.attempts END
        RETURNING attempts, (SELECT ts FROM clock)'''
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(sql, [period, f'{namespace}:{period}:', ':' + digest, namespace,
                period, period + 5, limit + 1])
            count, timestamp = cursor.fetchone()
    return count, period - (int(timestamp) % period)


def consume(identity, namespace, limit, period):
    try:
        backend = selected_backend()
        if backend == 'database':
            count, wait = database_consume(identity, namespace, limit, period)
        elif backend == 'redis':
            if not settings.REDIS_URL:
                raise RateLimitUnavailable()
            if not settings.DEBUG and settings.CACHES['default']['BACKEND'] != 'django.core.cache.backends.redis.RedisCache':
                raise RateLimitUnavailable()
            now = time.time()
            family, scope = namespace.split(':', 1)
            salt = 'login-quota' if family == 'login' else 'submission-quota'
            digest = salted_hmac(salt, identity, algorithm='sha256').hexdigest()
            prefix = 'admin-login' if family == 'login' else 'submission'
            key = f'{prefix}:{scope}:{int(now // period)}:{digest}'
            cache.add(key, 0, timeout=period + 5)
            count = cache.incr(key)
            wait = max(1, math.ceil(period - now % period))
        else:
            raise RateLimitUnavailable()
    except Exception:
        # No provider credentials, database error or identity is exposed.
        raise RateLimitUnavailable() from None
    # Raise outside atomic: rejected attempts must remain counted, not rolled back.
    if count > limit:
        raise Throttled(wait=max(1, wait))
