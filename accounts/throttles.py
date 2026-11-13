from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle
from .rate_limits import consume, RateLimitUnavailable


class LoginUnavailable(APIException):
    status_code = 503
    default_detail = 'Administrator login is temporarily unavailable.'


def quota(identity, name, limit, period):
    try:
        consume(identity, f'login:{name}', limit, period)
    except RateLimitUnavailable:
        raise LoginUnavailable() from None


def limit_login(request, username):
    identity = BaseThrottle().get_ident(request)
    quota(identity, 'ip-minute', settings.LOGIN_RATE_PER_MINUTE, 60)
    quota(identity, 'ip-hour', settings.LOGIN_RATE_PER_HOUR, 3600)
    quota(username.strip().casefold()[:150], 'username', settings.LOGIN_USERNAME_RATE_PER_15_MINUTES, 900)
