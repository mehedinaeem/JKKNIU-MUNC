import math
import time
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException, Throttled
from rest_framework.throttling import BaseThrottle


class LoginUnavailable(APIException):
    status_code = 503
    default_detail = 'Administrator login is temporarily unavailable.'


def quota(identity, name, limit, period):
    if not settings.DEBUG and not settings.REDIS_URL:
        raise LoginUnavailable()
    now = time.time()
    key = f'admin-login:{name}:{int(now // period)}:{salted_hmac("login-quota", identity, algorithm="sha256").hexdigest()}'
    try:
        cache.add(key, 0, timeout=period + 5)
        count = cache.incr(key)
    except Exception:
        raise LoginUnavailable() from None
    if count > limit:
        raise Throttled(wait=max(1, math.ceil(period - now % period)))


def limit_login(request, username):
    identity = BaseThrottle().get_ident(request)
    quota(identity, 'ip-minute', settings.LOGIN_RATE_PER_MINUTE, 60)
    quota(identity, 'ip-hour', settings.LOGIN_RATE_PER_HOUR, 3600)
    quota(username.strip().casefold()[:150], 'username', settings.LOGIN_USERNAME_RATE_PER_15_MINUTES, 900)
