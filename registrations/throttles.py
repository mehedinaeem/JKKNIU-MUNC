from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle
from accounts.rate_limits import consume, RateLimitUnavailable


class SubmissionUnavailable(APIException):
    status_code = 503
    default_detail = 'Submissions are temporarily unavailable. Please try again later.'


def consume_quota(identity, scope, limit, period):
    try:
        consume(identity, f'submission:{scope}', limit, period)
    except RateLimitUnavailable:
        raise SubmissionUnavailable() from None


class SubmissionIPThrottle(BaseThrottle):
    def allow_request(self, request, view):
        identity = self.get_ident(request)
        consume_quota(identity, 'minute', settings.SUBMISSION_RATE_PER_MINUTE, 60)
        consume_quota(identity, 'hour', settings.SUBMISSION_RATE_PER_HOUR, 3600)
        return True


def throttle_email(email):
    consume_quota(email, 'email', settings.SUBMISSION_EMAIL_RATE_PER_HOUR, 3600)
