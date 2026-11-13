import html
from django.conf import settings
from django.core import signing
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import ValidationError
from registrations.models import FormSubmission
from .models import EmailCampaign, EmailMessage, EmailPreference
from .notifications import context_for
from .rendering import render


class CampaignLimit(Exception):
    pass


def recipients(campaign):
    filters = campaign.recipient_filter
    rows = FormSubmission.objects.filter(event_id=campaign.event_id).select_related('event', 'registration_form', 'form_version').order_by('submitted_at', 'id')
    if filters.get('form_ids'):
        rows = rows.filter(registration_form_id__in=filters['form_ids'])
    if filters.get('statuses'):
        rows = rows.filter(status__in=filters['statuses'])
    if filters.get('form_types'):
        rows = rows.filter(registration_form__form_type__in=filters['form_types'])
    if filters.get('submission_ids'):
        rows = rows.filter(pk__in=filters['submission_ids'])
    payment = filters.get('payment_status')
    if payment == 'verified': rows = rows.filter(payment__status='verified')
    elif payment == 'unpaid': rows = rows.exclude(payment__status='verified')
    unique = {}
    for index, row in enumerate(rows.iterator()):
        if index >= 50000:
            raise ValidationError({'recipients': 'Narrow this campaign to fewer registration records.'})
        email = row.applicant_email.strip().casefold()
        try: validate_email(email)
        except Exception: continue
        unique.setdefault(email, row)
        if len(unique) > settings.EMAIL_CAMPAIGN_MAX_RECIPIENTS:
            raise ValidationError({'recipients': 'Too many recipients. Narrow the selected event/form/status.'})
    preferences = {item.email: item for item in EmailPreference.objects.filter(email__in=unique)}
    return [(email, row) for email, row in unique.items() if not (preferences.get(email) and preferences[email].suppressed)
        and (campaign.classification != 'marketing' or (preferences.get(email) and preferences[email].marketing_opt_in and not preferences[email].unsubscribed_at))]


def unsubscribe_url(email):
    preference, _ = EmailPreference.objects.get_or_create(email=email)
    token = signing.dumps({'preference': preference.pk}, salt='munc-mail-unsubscribe')
    return f'{settings.PUBLIC_API_URL}/email/unsubscribe/?token={token}'


def campaign_content(campaign, row, email, opt_out_url=None):
    subject, body, text = render(campaign.subject, campaign.html_content, campaign.text_content, context_for(row))
    if campaign.classification == 'marketing':
        url = opt_out_url or unsubscribe_url(email)
        body += f'<p><a href="{html.escape(url, quote=True)}">Unsubscribe from optional announcements</a></p>'
        text += '\n\nUnsubscribe from optional announcements: ' + url
    return subject, body, text


@transaction.atomic
def activate_campaign(pk):
    campaign = EmailCampaign.objects.select_for_update().get(pk=pk)
    if campaign.snapshot_at or campaign.status not in {'ready', 'scheduled'} or (campaign.scheduled_at and campaign.scheduled_at > timezone.now()):
        return
    selected = recipients(campaign)
    if not selected:
        campaign.status = 'completed'
        campaign.completed_at = timezone.now()
    else:
        jobs, total = [], 0
        for email, row in selected:
            opt_out = unsubscribe_url(email) if campaign.classification == 'marketing' else None
            subject, body, text = campaign_content(campaign, row, email, opt_out)
            headers = {'List-Unsubscribe': f'<{opt_out}>', 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'} if opt_out else {}
            total += len(body.encode()) + len(text.encode())
            if total > 20 * 1024 * 1024:
                raise CampaignLimit('Campaign content exceeds the supported snapshot size. Narrow recipients.')
            jobs.append(EmailMessage(event_key=f'campaign:{campaign.pk}:{salted_hmac("mail-campaign", email).hexdigest()}', event=campaign.event,
                submission=row, campaign=campaign, recipient_email=email, message_type=campaign.template.template_key if campaign.template_id else 'custom_announcement',
                classification=campaign.classification, subject=subject, html_content=body, text_content=text, extra_headers=headers))
        EmailMessage.objects.bulk_create(jobs, batch_size=200)
        campaign.status = 'sending'
    campaign.snapshot_at = timezone.now()
    campaign.started_at = timezone.now()
    campaign.save()


def activate_due():
    for pk in EmailCampaign.objects.filter(Q(status='ready') | Q(status='scheduled', scheduled_at__lte=timezone.now())).values_list('pk', flat=True):
        try:
            activate_campaign(pk)
        except (ValidationError, CampaignLimit):
            EmailCampaign.objects.filter(pk=pk, status__in=['ready', 'scheduled']).update(status='failed', last_error='Recipient selection or content exceeds limits. Review the draft and narrow selection.')
