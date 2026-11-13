from datetime import timedelta
from zoneinfo import ZoneInfo
import time
from django.conf import settings
from django.db import connection, transaction
from django.db.models import Case, IntegerField, Q, When
from django.utils import timezone
from .campaigns import activate_due, unsubscribe_url
from .models import EmailCampaign, EmailDailyQuota, EmailDeliveryAttempt, EmailMessage, EmailPreference, EmailSystemState
from .notifications import reconcile, event_settings
from .providers import get_provider

PENDING = ['pending', 'retry']


def quota_day(now=None):
    return (now or timezone.now()).astimezone(ZoneInfo(settings.EMAIL_QUOTA_TIME_ZONE)).date()


@transaction.atomic
def claim(transactional_only=False):
    now = timezone.now()
    quota, _ = EmailDailyQuota.objects.get_or_create(day=quota_day(now), defaults={'next_send_at': now})
    quota = EmailDailyQuota.objects.select_for_update().get(pk=quota.pk)
    if quota.used >= settings.EMAIL_DAILY_LIMIT:
        return None, 'quota'
    if quota.next_send_at > now:
        return None, 'rate'
    candidates = EmailMessage.objects.filter(status__in=PENDING, next_attempt_at__lte=now).filter(
        Q(campaign__isnull=True) | Q(campaign__status='sending')).annotate(
            priority=Case(When(message_type__in=['membership_invitation', 'membership_password_reset', 'membership_email_verification'], then=0), When(classification='transactional', then=1), default=2, output_field=IntegerField())).order_by('priority', 'created_at', 'id')
    if transactional_only or quota.bulk_used >= settings.EMAIL_DAILY_LIMIT - settings.EMAIL_TRANSACTIONAL_RESERVE:
        candidates = candidates.filter(classification='transactional')
    # Lock only the job row; nullable joins cannot be FOR UPDATE targets on PostgreSQL.
    locked = candidates.select_for_update(skip_locked=True, of=('self',)) if connection.vendor == 'postgresql' else candidates.select_for_update()
    message = locked.first()
    if not message:
        return None, 'empty'
    if message.event_key.startswith('membership:invitation:'):
        from membership.models import ActivationInvitation
        invitation = ActivationInvitation.objects.filter(pk=message.event_key.split(':')[-1]).first()
        if not invitation or invitation.used_at or invitation.revoked_at or invitation.expires_at <= now:
            message.status, message.last_error = 'skipped', 'Private invitation is no longer valid.'
            message.html_content = message.text_content = ''
            message.save()
            return None, 'skipped'
    if message.campaign_id:
        campaign = EmailCampaign.objects.select_for_update().get(pk=message.campaign_id)
        if campaign.status != 'sending':
            return None, 'empty'
    config = event_settings(message.event_id) if message.classification == 'transactional' else None
    auto_disabled = config and ((message.message_type == 'registration_confirmation' and not config.registration_enabled)
        or (message.message_type == 'payment_verified' and not config.payment_enabled)
        or (message.message_type.startswith('application_') and message.message_type.removeprefix('application_') not in config.status_notifications))
    if auto_disabled:
        message.status, message.last_error = 'skipped', 'Automatic notification disabled for this event.'
        message.save()
        return None, 'skipped'
    preference = EmailPreference.objects.filter(email=message.recipient_email).first()
    if not message.recipient_email or (preference and (preference.suppressed or (message.classification == 'marketing' and (not preference.marketing_opt_in or preference.unsubscribed_at)))) or (message.classification == 'marketing' and not preference):
        message.status = 'skipped'
        message.last_error = 'Recipient suppressed or optional consent withdrawn.'
        message.save()
        return None, 'skipped'
    message.sender_email = message.sender_email or settings.DEFAULT_FROM_EMAIL
    message.sender_name = message.sender_name or settings.DEFAULT_FROM_NAME
    message.status = 'sending'
    message.claimed_at = now
    message.attempt_count += 1
    message.save()
    quota.used += 1
    if message.classification != 'transactional': quota.bulk_used += 1
    quota.next_send_at = now + timedelta(seconds=60 / settings.EMAIL_RATE_PER_MINUTE)
    quota.save()
    return message, 'claimed'


@transaction.atomic
def finish(message_id, result):
    message = EmailMessage.objects.select_for_update().get(pk=message_id)
    EmailDeliveryAttempt.objects.get_or_create(message=message, number=message.attempt_count,
        defaults={'outcome': result.outcome, 'http_status': result.http_status, 'detail': result.error[:255]})
    if result.message_id:
        message.provider_message_id = result.message_id
    if result.outcome == 'accepted':
        message.accepted_at = message.accepted_at or timezone.now()
    # A delivery webhook can arrive while the HTTP request is still in flight.
    if message.status != 'sending':
        message.save(update_fields=['provider_message_id', 'accepted_at', 'updated_at'])
        return
    message.status = result.outcome
    message.last_error = result.error[:255]
    message.retryable = result.outcome == 'retry'
    if result.outcome == 'accepted':
        message.accepted_at = timezone.now()
    if result.outcome == 'retry':
        message.retry_count += 1
        if message.retry_count >= settings.EMAIL_MAX_ATTEMPTS:
            message.status = 'failed'
        else:
            delay = max(result.retry_after, min(86400, settings.EMAIL_RETRY_BASE_SECONDS * (2 ** (message.retry_count - 1))))
            message.next_attempt_at = timezone.now() + timedelta(seconds=delay)
    message.save()


def refresh_campaigns():
    for campaign in EmailCampaign.objects.filter(status='sending'):
        if not campaign.messages.filter(status__in=[*PENDING, 'sending', 'unknown']).exists():
            EmailCampaign.objects.filter(pk=campaign.pk, status='sending').update(status='completed', completed_at=timezone.now())


def process(limit=50, transactional_only=False, dry_run=False):
    if dry_run:
        jobs = EmailMessage.objects.filter(status__in=PENDING, next_attempt_at__lte=timezone.now())
        if transactional_only: jobs = jobs.filter(classification='transactional')
        return {'dry_run': True, 'eligible_jobs': jobs.count(), 'transport_enabled': settings.EMAIL_ENABLED}
    if not settings.EMAIL_ENABLED:
        return {'processed': 0, 'reason': 'Email transport disabled; durable jobs retained.'}
    if not settings.BREVO_API_KEY or not settings.DEFAULT_FROM_EMAIL or not settings.PUBLIC_SITE_URL or not settings.PUBLIC_API_URL:
        return {'processed': 0, 'reason': 'Configure provider, verified sender and public site URL first.'}
    reconcile()
    if not transactional_only: activate_due()
    cutoff = timezone.now() - timedelta(seconds=settings.EMAIL_LEASE_SECONDS)
    EmailMessage.objects.filter(status='sending', claimed_at__lt=cutoff).update(status='unknown', last_error='Worker lease expired. Provider acceptance is unknown; reconcile before further action.')
    state, _ = EmailSystemState.objects.get_or_create(pk=1)
    EmailSystemState.objects.filter(pk=state.pk).update(last_worker_at=timezone.now())
    count, skipped = 0, 0
    deadline = time.monotonic() + 300
    while count < limit and time.monotonic() < deadline:
        message, reason = claim(transactional_only)
        if reason == 'rate':
            time.sleep(min(1, 60 / settings.EMAIL_RATE_PER_MINUTE))
            continue
        if reason == 'skipped':
            skipped += 1
            if skipped >= limit * 2: break
            continue
        if not message: break
        from .providers import SendResult
        try: result = get_provider().send(message, message.extra_headers)
        except Exception: result = SendResult('unknown', error='Unexpected transport outcome. Reconcile with provider logs.')
        finish(message.pk, result)
        count += 1
    refresh_campaigns()
    return {'processed': count, 'skipped': skipped}
