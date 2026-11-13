import hashlib
import hmac
from datetime import datetime, timezone as utc
import uuid
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from registrations.parsers import BoundedJSONParser
from .models import EmailMessage, EmailPreference, EmailWebhookEvent

EVENTS = {'request': 'accepted', 'sent': 'accepted', 'delivered': 'delivered', 'deferred': 'deferred',
    'soft_bounce': 'soft_bounced', 'softBounce': 'soft_bounced', 'hard_bounce': 'hard_bounced', 'hardBounce': 'hard_bounced',
    'blocked': 'blocked', 'invalid': 'failed', 'error': 'failed', 'spam': 'blocked'}


@transaction.atomic
def apply_event(data):
    if not isinstance(data, dict): raise ValidationError('Invalid webhook event.')
    event = data.get('event')
    if event not in {*EVENTS, 'unsubscribed'}: return
    provider_id = str(data.get('message-id', ''))[:500].strip('<>')
    custom = data.get('X-Mailin-custom', '')
    message = None
    # Custom opaque correlation handles callbacks arriving before the send response.
    if isinstance(custom, str) and custom.startswith('munc-message:'):
        try: pk = uuid.UUID(custom.split(':', 1)[1])
        except (ValueError, TypeError): pk = None
        if pk: message = EmailMessage.objects.select_for_update().filter(pk=pk).first()
    if not message and provider_id:
        message = EmailMessage.objects.select_for_update().filter(provider_message_id=provider_id).first()
    if not message or message.redacted_at: return
    if str(data.get('email', '')).strip().casefold() != message.recipient_email:
        raise ValidationError('Webhook correlation mismatch.')
    if message.provider_message_id and provider_id and message.provider_message_id != provider_id:
        raise ValidationError('Webhook correlation mismatch.')
    stamp = data.get('ts_event', data.get('ts', data.get('ts_epoch')))
    try:
        seconds = float(stamp)
        if seconds > 1e12: seconds /= 1000
        occurred = datetime.fromtimestamp(seconds, tz=utc.utc)
        if occurred > timezone.now() + timezone.timedelta(minutes=5): raise ValueError()
    except (ValueError, TypeError, OverflowError, OSError):
        raise ValidationError('A valid webhook event timestamp is required.') from None
    fingerprint = hashlib.sha256(f'{message.pk}|{event}|{provider_id}|{occurred.isoformat()}'.encode()).hexdigest()
    _, created = EmailWebhookEvent.objects.get_or_create(fingerprint=fingerprint, defaults={'message': message, 'event_type': event, 'occurred_at': occurred})
    if not created: return
    if event in {'hard_bounce', 'hardBounce', 'invalid', 'spam', 'blocked', 'unsubscribed'}:
        pref, _ = EmailPreference.objects.get_or_create(email=message.recipient_email)
        if event == 'unsubscribed':
            pref.marketing_opt_in, pref.unsubscribed_at = False, timezone.now()
        else:
            pref.suppressed, pref.suppression_reason = True, event
        pref.save()
    if message.last_event_at and occurred < message.last_event_at:
        return
    # Delivery must never be inferred from acceptance; later deferrals cannot undo delivery.
    target = EVENTS.get(event, message.status)
    if message.delivered_at and target in {'accepted', 'deferred', 'soft_bounced'}:
        return
    message.provider_message_id = message.provider_message_id or provider_id
    message.last_event_at = occurred
    if target == 'accepted': message.accepted_at = message.accepted_at or occurred
    if target == 'delivered':
        message.accepted_at = message.accepted_at or occurred
        message.delivered_at = occurred
    message.status = target
    message.retryable = False
    if target in {'failed', 'hard_bounced', 'blocked'}: message.last_error = f'Provider reported {event}.'
    message.save()


class BrevoWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [BoundedJSONParser]

    def post(self, request):
        expected = settings.BREVO_WEBHOOK_TOKEN
        supplied = request.headers.get('Authorization', '')
        if not expected or not hmac.compare_digest(supplied.encode('utf-8'), f'Bearer {expected}'.encode('utf-8')):
            raise PermissionDenied('Webhook authentication failed.')
        rows = request.data if isinstance(request.data, list) else [request.data]
        if len(rows) > 100: raise ValidationError('Webhook batch exceeds the supported size.')
        for row in rows: apply_event(row)
        from .queue import refresh_campaigns
        refresh_campaigns()
        return Response({'received': True})


class Unsubscribe(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def email(self, request):
        token = request.query_params.get('token', '')
        try:
            value = signing.loads(token, salt='munc-mail-unsubscribe')
            pk = value['preference']
            if type(pk) is not int: raise ValueError()
            preference = EmailPreference.objects.filter(pk=pk).first()
            if not preference: raise ValueError()
            return preference.email
        except (signing.BadSignature, ValueError, KeyError, TypeError):
            raise ValidationError('This unsubscribe link is invalid.') from None

    def get(self, request):
        self.email(request)
        # Capability link grants only opt-out; GET never mutates consent.
        response = HttpResponse('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Unsubscribe — JKKNIU MUNC</title><h1>Optional announcements</h1><p>You can stop optional announcements. Necessary updates about your applications may still be sent.</p><form method="post"><button type="submit">Unsubscribe</button></form></html>', content_type='text/html')
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        response['Content-Security-Policy'] = "default-src 'none'; form-action 'self'; frame-ancestors 'none'"
        return response

    def post(self, request):
        email = self.email(request)
        pref, _ = EmailPreference.objects.get_or_create(email=email)
        pref.marketing_opt_in, pref.unsubscribed_at = False, timezone.now()
        pref.save()
        response = Response({'message': 'You have been unsubscribed from optional announcements.'})
        response['Cache-Control'] = 'no-store'
        return response
