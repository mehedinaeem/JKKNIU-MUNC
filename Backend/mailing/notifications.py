from urllib.parse import quote
from django.conf import settings
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from registrations.models import FormSubmission, SubmissionStatusChange
from .defaults import DEFAULTS
from .models import EmailMessage, EmailTemplate, EmailSystemState, EventEmailSettings, PaymentChange
from .rendering import render

STATUS_KEYS = ['submitted', 'under_review', 'shortlisted', 'approved', 'rejected', 'waitlisted']


def event_settings(event_id):
    return EventEmailSettings.objects.filter(event_id=event_id).first()


def context_for(submission, status=None, instructions=None, payment=None):
    full_name = 'Applicant'
    for field in submission.form_version.schema.get('fields', []):
        if field['field_type'] in {'short_text', 'long_text'} and (field['key'] in {'name', 'full_name'} or 'full name' in field['label'].casefold() or field['label'].strip().casefold() in {'name', 'applicant name', 'your name', 'preferred name', 'legal name', 'নাম', 'পূর্ণ নাম'}):
            value = submission.answers.get(field['key'])
            if isinstance(value, str) and value.strip():
                full_name = value.strip()[:255]
                break
    current = status or submission.status
    config = event_settings(submission.event_id)
    next_steps = instructions if instructions is not None else ((config.status_instructions.get(current) or config.next_instructions) if config else '')
    next_steps = next_steps or 'Please keep your registration reference and follow the official event updates.'
    event = submission.event
    return {'full_name': full_name, 'first_name': full_name.split()[0], 'event_name': event.title,
        'registration_id': submission.reference_number, 'registration_type': submission.form_version.schema.get('title', submission.registration_form.title),
        'application_status': dict(FormSubmission.Status.choices).get(current, current),
        'event_date': timezone.localtime(event.start_date).strftime('%d %B %Y, %H:%M %Z'), 'event_venue': event.venue,
        'submission_date': timezone.localtime(submission.submitted_at).strftime('%d %B %Y, %H:%M %Z'),
        'next_instructions': next_steps,
        'event_url': f'{settings.PUBLIC_SITE_URL}/events/{quote(event.slug)}',
        'payment_amount': (payment or {}).get('payment_amount', 'Not recorded'),
        'verified_at': (payment or {}).get('verified_at', '')}


def template_content(key, event_id):
    template = EmailTemplate.objects.filter(event_id=event_id, template_key=key).first() or EmailTemplate.objects.filter(event__isnull=True, template_key=key).first()
    if template:
        return {'subject': template.subject, 'html_content': template.html_content, 'text_content': template.text_content} if template.is_active else None
    default = DEFAULTS.get(key, DEFAULTS['custom_announcement'])
    return {attribute: default[attribute] for attribute in ('subject', 'html_content', 'text_content')}


@transaction.atomic
def queue_notification(kind, pk):
    if not settings.PUBLIC_SITE_URL:
        return None  # Reconciliation will render once the operator configures official URLs.
    state, _ = EmailSystemState.objects.get_or_create(pk=1)
    change = None
    if kind == 'registration':
        submission = FormSubmission.objects.select_related('event', 'registration_form', 'form_version').get(pk=pk)
        happened_at = submission.submitted_at
        key, message_type, status = f'registration:{pk}', 'registration_confirmation', 'submitted'
    elif kind == 'status':
        change = SubmissionStatusChange.objects.select_related('submission__event', 'submission__registration_form', 'submission__form_version').get(pk=pk)
        submission, happened_at = change.submission, change.created_at
        key, status = f'status:{pk}', change.status
        message_type = f'application_{status}'
    else:
        change = PaymentChange.objects.select_related('submission__event', 'submission__registration_form', 'submission__form_version').get(pk=pk)
        submission, happened_at = change.submission, change.created_at
        key, message_type, status = f'payment:{pk}', 'payment_verified', submission.status
        if change.status != 'verified':
            return None
    if happened_at < state.created_at or EmailMessage.objects.filter(event_key=key).exists():
        return None
    email = submission.applicant_email.strip().casefold()
    try:
        validate_email(email)
    except Exception:
        return None
    config = event_settings(submission.event_id)
    enabled = not config or (config.registration_enabled if kind == 'registration' else config.payment_enabled if kind == 'payment' else status in config.status_notifications)
    content = template_content(message_type, submission.event_id)
    context = context_for(submission, status=status, payment=change.details if kind == 'payment' else None,
        instructions=change.details.get('next_instructions') if kind == 'payment' and 'next_instructions' in change.details else None)
    subject, html, text = render(**(content or template_content('custom_announcement', submission.event_id) or DEFAULTS['custom_announcement']), context=context) if content else ('Notification disabled', '', '')
    defaults = {'recipient_email': email, 'event': submission.event, 'submission': submission, 'message_type': message_type,
        'subject': subject, 'html_content': html, 'text_content': text, 'status': 'pending' if enabled and content else 'skipped'}
    if kind == 'status':
        defaults['status_change'] = change
    if kind == 'payment':
        defaults['payment_change'] = change
    return EmailMessage.objects.get_or_create(event_key=key, defaults=defaults)[0]


def reconcile(limit=500):
    state, _ = EmailSystemState.objects.get_or_create(pk=1)
    sources = [
        ('registration', FormSubmission.objects.filter(submitted_at__gte=state.created_at).exclude(email_messages__message_type='registration_confirmation')),
        ('status', SubmissionStatusChange.objects.filter(created_at__gte=state.created_at, email_messages__isnull=True)),
        ('payment', PaymentChange.objects.filter(created_at__gte=state.created_at, status='verified', email_messages__isnull=True)),
    ]
    for kind, query in sources:
        for pk in query.order_by('pk').values_list('pk', flat=True)[:limit]:
            queue_notification(kind, pk)
