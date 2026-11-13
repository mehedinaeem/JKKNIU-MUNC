from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from mailing.models import EmailMessage, EmailDeliveryAttempt


class Command(BaseCommand):
    help = 'Redact aged terminal email PII while retaining idempotency tombstones, consent and suppression.'
    def add_arguments(self, parser): parser.add_argument('--dry-run', action='store_true')
    def handle(self, *args, **options):
        rows = EmailMessage.objects.filter(updated_at__lt=timezone.now()-timedelta(days=settings.EMAIL_RETENTION_DAYS),
            status__in=['accepted', 'delivered', 'deferred', 'soft_bounced', 'failed', 'hard_bounced', 'blocked', 'cancelled', 'skipped'], redacted_at__isnull=True)
        count = rows.count()
        if not options['dry_run']:
            EmailDeliveryAttempt.objects.filter(message__in=rows).update(detail='')
            rows.update(recipient_email='', subject='[retained delivery record]', html_content='', text_content='', last_error='', extra_headers={}, redacted_at=timezone.now())
        self.stdout.write(f'{count} terminal records eligible for redaction.')
