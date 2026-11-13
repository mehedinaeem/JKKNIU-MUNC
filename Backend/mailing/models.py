import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    template_key = models.SlugField(max_length=100)
    event = models.ForeignKey('events.Event', null=True, blank=True, on_delete=models.PROTECT)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_key', 'id']
        constraints = [models.UniqueConstraint(fields=['event', 'template_key'], condition=Q(event__isnull=False), name='mail_event_template_key'), models.UniqueConstraint(fields=['template_key'], condition=Q(event__isnull=True), name='mail_global_template_key')]


class EventEmailSettings(models.Model):
    event = models.OneToOneField('events.Event', on_delete=models.PROTECT, related_name='email_settings')
    registration_enabled = models.BooleanField(default=True)
    payment_enabled = models.BooleanField(default=True)
    status_notifications = models.JSONField(default=list)
    next_instructions = models.TextField(blank=True)
    status_instructions = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)


class EmailCampaign(models.Model):
    event = models.ForeignKey('events.Event', on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    template = models.ForeignKey(EmailTemplate, null=True, blank=True, on_delete=models.PROTECT)
    html_content = models.TextField()
    text_content = models.TextField()
    classification = models.CharField(max_length=20, choices=[('operational', 'Operational event update'), ('marketing', 'Optional marketing')], default='operational')
    recipient_filter = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='draft', db_index=True, choices=[(s, s) for s in ['draft', 'ready', 'scheduled', 'sending', 'paused', 'completed', 'cancelled', 'failed']])
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    snapshot_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class EmailPreference(models.Model):
    email = models.EmailField(unique=True)
    marketing_opt_in = models.BooleanField(default=False)
    consent_evidence = models.TextField(blank=True)
    consent_recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    suppressed = models.BooleanField(default=False)
    suppression_reason = models.CharField(max_length=40, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PaymentVerification(models.Model):
    submission = models.OneToOneField('registrations.FormSubmission', on_delete=models.PROTECT, related_name='payment')
    status = models.CharField(max_length=12, choices=[(s, s) for s in ['unpaid', 'pending', 'verified', 'rejected']], default='unpaid')
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='BDT')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    verified_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PaymentChange(models.Model):
    submission = models.ForeignKey('registrations.FormSubmission', on_delete=models.PROTECT)
    previous_status = models.CharField(max_length=12)
    status = models.CharField(max_length=12)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class EmailMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        RETRY = 'retry'
        SENDING = 'sending'
        ACCEPTED = 'accepted'
        DELIVERED = 'delivered'
        DEFERRED = 'deferred'
        SOFT_BOUNCED = 'soft_bounced'
        HARD_BOUNCED = 'hard_bounced'
        BLOCKED = 'blocked'
        FAILED = 'failed'
        UNKNOWN = 'unknown'
        CANCELLED = 'cancelled'
        SKIPPED = 'skipped'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_key = models.CharField(max_length=255, unique=True)
    recipient_email = models.EmailField()
    event = models.ForeignKey('events.Event', on_delete=models.PROTECT)
    submission = models.ForeignKey('registrations.FormSubmission', null=True, blank=True, on_delete=models.PROTECT, related_name='email_messages')
    status_change = models.ForeignKey('registrations.SubmissionStatusChange', null=True, blank=True, on_delete=models.PROTECT, related_name='email_messages')
    payment_change = models.ForeignKey(PaymentChange, null=True, blank=True, on_delete=models.PROTECT, related_name='email_messages')
    campaign = models.ForeignKey(EmailCampaign, null=True, blank=True, on_delete=models.PROTECT, related_name='messages')
    message_type = models.CharField(max_length=100)
    classification = models.CharField(max_length=20, default='transactional')
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField()
    extra_headers = models.JSONField(default=dict)
    sender_email = models.EmailField(blank=True)
    sender_name = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=20, default='brevo')
    provider_message_id = models.CharField(max_length=500, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempt_count = models.PositiveIntegerField(default=0)
    retry_count = models.PositiveIntegerField(default=0)
    retryable = models.BooleanField(default=False)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    redacted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['status', 'next_attempt_at'], name='mail_due_jobs_idx')]
        constraints = [models.UniqueConstraint(fields=['campaign', 'recipient_email'], condition=Q(campaign__isnull=False) & ~Q(recipient_email=''), name='mail_campaign_unique_recipient')]


class EmailDeliveryAttempt(models.Model):
    message = models.ForeignKey(EmailMessage, on_delete=models.PROTECT, related_name='attempts')
    number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=30)
    http_status = models.PositiveIntegerField(null=True)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [models.UniqueConstraint(fields=['message', 'number'], name='mail_unique_attempt')]


class EmailDailyQuota(models.Model):
    day = models.DateField(unique=True)
    used = models.PositiveIntegerField(default=0)
    bulk_used = models.PositiveIntegerField(default=0)
    next_send_at = models.DateTimeField(default=timezone.now)


class EmailSystemState(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    last_worker_at = models.DateTimeField(null=True, blank=True)


class EmailWebhookEvent(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True)
    message = models.ForeignKey(EmailMessage, on_delete=models.PROTECT, related_name='webhook_events')
    event_type = models.CharField(max_length=30)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
