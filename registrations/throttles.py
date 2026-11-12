import math
import time
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException, Throttled
from rest_framework.throttling import BaseThrottle


class SubmissionUnavailable(APIException):
    status_code = 503
    default_detail = 'Submissions are temporarily unavailable. Please try again later.'


def consume_quota(identity, scope, limit, period):
    if not settings.DEBUG and not settings.REDIS_URL:
        raise SubmissionUnavailable()
    now = time.time()
    bucket = int(now // period)
    digest = salted_hmac('submission-quota', identity, algorithm='sha256').hexdigest()
    key = f'submission:{scope}:{bucket}:{digest}'
    try:
        cache.add(key, 0, timeout=period + 5)
        count = cache.incr(key)
    except Exception:
        raise SubmissionUnavailable() from None
    if count > limit:
        raise Throttled(wait=max(1, math.ceil(period - now % period)))


class SubmissionIPThrottle(BaseThrottle):
    def allow_request(self, request, view):
        identity = self.get_ident(request)
        consume_quota(identity, 'minute', settings.SUBMISSION_RATE_PER_MINUTE, 60)
        consume_quota(identity, 'hour', settings.SUBMISSION_RATE_PER_HOUR, 3600)
        return True


def throttle_email(email):
    consume_quota(email, 'email', settings.SUBMISSION_EMAIL_RATE_PER_HOUR, 3600)
