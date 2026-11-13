"""Only transport module knows Brevo credentials; no raw provider responses are logged."""
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from django.conf import settings
import requests


@dataclass
class SendResult:
    outcome: str
    message_id: str = ''
    http_status: int | None = None
    error: str = ''
    retry_after: int = 0


class BrevoProvider:
    def send(self, message, headers=None):
        if not settings.BREVO_API_KEY or not message.sender_email:
            return SendResult('failed', error='Email provider/sender is not configured.')
        html, text = message.html_content, message.text_content
        from membership.crypto import SECURITY_TYPES, unseal
        if message.message_type in SECURITY_TYPES:
            try: html, text = unseal(html), unseal(text)
            except Exception: return SendResult('failed', error='Private email could not be decrypted; restore the server key or issue a new invitation.')
        payload = {'sender': {'email': message.sender_email, 'name': message.sender_name},
            'to': [{'email': message.recipient_email}], 'subject': message.subject,
            'htmlContent': html, 'textContent': text,
            'headers': {'idempotencyKey': str(message.pk), 'X-Mailin-custom': f'munc-message:{message.pk}', **(headers or {})},
            'tags': ['munc', message.message_type[:50]]}
        try:
            response = requests.post('https://api.brevo.com/v3/smtp/email', json=payload,
                headers={'api-key': settings.BREVO_API_KEY, 'Accept': 'application/json', 'Content-Type': 'application/json'},
                timeout=(settings.EMAIL_CONNECT_TIMEOUT, settings.EMAIL_READ_TIMEOUT), allow_redirects=False)
        except requests.exceptions.ConnectTimeout:
            return SendResult('retry', error='Provider connection timed out before sending.')
        except requests.RequestException:
            return SendResult('unknown', error='Provider outcome unknown after a network failure. Check provider logs; do not resend automatically.')
        try:
            if response.status_code == 201:
                try:
                    message_id = response.json().get('messageId', '')
                except (ValueError, AttributeError, TypeError):
                    message_id = ''
                if isinstance(message_id, str) and 0 < len(message_id) <= 500 and not any(c in message_id for c in '\r\n'):
                    return SendResult('accepted', message_id=message_id.strip('<>'), http_status=201)
                return SendResult('unknown', http_status=201, error='Provider accepted the request without a usable message ID; reconcile in provider logs.')
            if response.status_code == 429:
                value = response.headers.get('Retry-After', '60')
                try:
                    delay = int(value)
                except ValueError:
                    try: delay = int((parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
                    except (ValueError, TypeError): delay = 60
                return SendResult('retry', http_status=429, error='Provider rate limit reached.', retry_after=max(1, min(delay, 86400)))
            if response.status_code >= 500 or response.status_code in {408, 409}:
                return SendResult('unknown', http_status=response.status_code, error='Provider outcome is uncertain. Check provider logs before any further action.')
            # A duplicate idempotency response can mean an earlier request was accepted.
            try: duplicate = response.json().get('code') == 'duplicate_parameter'
            except (ValueError, AttributeError): duplicate = False
            if duplicate:
                return SendResult('unknown', http_status=response.status_code, error='Provider detected an earlier request with this idempotency key; reconcile the original.')
            return SendResult('failed', http_status=response.status_code, error=f'Provider rejected request (HTTP {response.status_code}).')
        finally:
            response.close()


def get_provider():
    if settings.EMAIL_PROVIDER != 'brevo':
        raise ValueError('Unsupported email provider')
    return BrevoProvider()
