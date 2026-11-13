import uuid
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.roles import is_event_manager, is_super_admin, scope_queryset, can_manage_event
from accounts.permissions import ApplicationReviewPermission
from events.models import Event
from registrations.models import FormSubmission, ReviewAccessLog
from registrations.views import PrivateStaffResponseMixin
from .permissions import EmailPermission, EmailThrottle
from .models import EmailTemplate, EmailCampaign, EmailMessage, EmailPreference, EmailDailyQuota, EmailSystemState, EventEmailSettings, PaymentVerification, PaymentChange
from .serializers import PreviewContentSerializer, TemplateSerializer, CampaignSerializer, MessageSerializer, EventSettingsSerializer, RecipientCountSerializer
from .notifications import STATUS_KEYS, context_for
from .campaigns import recipients, campaign_content
from .queue import quota_day, refresh_campaigns
from .rendering import render, VARIABLES


class EmailBase(PrivateStaffResponseMixin):
    from registrations.parsers import BoundedJSONParser
    parser_classes = [BoundedJSONParser]
    permission_classes = [EmailPermission]
    throttle_classes = [EmailThrottle]


def audit(request, action, **metadata):
    ReviewAccessLog.objects.create(actor=request.user, action=f'email_{action}', metadata=metadata)


def scoped(model, request):
    return scope_queryset(model.objects.all(), request.user)


class Overview(EmailBase, APIView):
    def get(self, request):
        jobs = scoped(EmailMessage, request)
        counts = dict(jobs.values('status').annotate(total=Count('pk')).values_list('status', 'total'))
        quota = EmailDailyQuota.objects.filter(day=quota_day()).first()
        state = EmailSystemState.objects.filter(pk=1).first()
        return Response({'statuses': counts, 'total_queued': jobs.count(), 'accepted': jobs.filter(accepted_at__isnull=False).count(),
            'delivered': jobs.filter(delivered_at__isnull=False).count(), 'pending': jobs.filter(status__in=['pending', 'retry', 'sending']).count(),
            'failed': jobs.filter(status__in=['failed', 'hard_bounced', 'blocked']).count(), 'unknown': counts.get('unknown', 0),
            'approximate_remaining_quota': max(0, settings.EMAIL_DAILY_LIMIT - (quota.used if quota else 0)),
            'daily_limit': settings.EMAIL_DAILY_LIMIT, 'transactional_reserve': settings.EMAIL_TRANSACTIONAL_RESERVE,
            'enabled': settings.EMAIL_ENABLED, 'configured': bool(settings.BREVO_API_KEY and settings.DEFAULT_FROM_EMAIL and settings.PUBLIC_SITE_URL and settings.PUBLIC_API_URL),
            'provider': settings.EMAIL_PROVIDER, 'last_worker_at': state.last_worker_at if state else None})


class TemplateList(EmailBase, generics.ListCreateAPIView):
    serializer_class = TemplateSerializer
    def get_queryset(self):
        if is_super_admin(self.request.user): return EmailTemplate.objects.all()
        return EmailTemplate.objects.filter(Q(event__isnull=True) | Q(event_id__in=self.request.user.event_assignments.values('event_id')))
    def perform_create(self, serializer):
        try:
            with transaction.atomic(): instance = serializer.save()
        except IntegrityError: raise ValidationError({'template_key': 'A template with this key already exists in this scope.'}) from None
        audit(self.request, 'template_create', template=instance.pk)


class TemplateDetail(EmailBase, generics.RetrieveUpdateAPIView):
    serializer_class = TemplateSerializer
    http_method_names = ['get', 'patch', 'head', 'options']
    def get_queryset(self):
        if is_super_admin(self.request.user): return EmailTemplate.objects.all()
        return EmailTemplate.objects.filter(event_id__in=self.request.user.event_assignments.values('event_id'))
    def perform_update(self, serializer):
        try:
            with transaction.atomic(): instance = serializer.save()
        except IntegrityError: raise ValidationError({'template_key': 'A template with this key already exists in this scope.'}) from None
        audit(self.request, 'template_update', template=instance.pk)


class TemplatePreview(EmailBase, APIView):
    def post(self, request):
        serializer = PreviewContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data
        subject, body, text = render(content.get('subject', ''), content.get('html_content', ''), content.get('text_content', ''), example_context())
        return Response({'subject': subject, 'html_content': body, 'text_content': text})


def example_context():
    return dict.fromkeys(VARIABLES, '') | {'full_name': 'Example Applicant', 'first_name': 'Example', 'event_name': 'Example MUN Conference', 'registration_id': 'JM-EXAMPLE', 'registration_type': 'Example category', 'application_status': 'Submitted', 'event_date': 'Example event date', 'event_venue': 'Event venue', 'event_url': f'{settings.PUBLIC_SITE_URL}/events/example', 'next_instructions': 'Follow the official event announcements.', 'submission_date': 'Example submission date', 'payment_amount': 'BDT 0.00', 'verified_at': 'Example verification date'}


class CampaignList(EmailBase, generics.ListCreateAPIView):
    serializer_class = CampaignSerializer
    def get_queryset(self):
        rows = scoped(EmailCampaign, self.request).select_related('event')
        if self.request.query_params.get('status'):
            rows = rows.filter(status=self.request.query_params['status'])
        return rows
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        audit(self.request, 'campaign_create', campaign=instance.pk)


class CampaignDetail(EmailBase, generics.RetrieveUpdateAPIView):
    serializer_class = CampaignSerializer
    http_method_names = ['get', 'patch', 'head', 'options']
    def get_queryset(self): return scoped(EmailCampaign, self.request).select_related('event')
    def perform_update(self, serializer):
        with transaction.atomic():
            locked = EmailCampaign.objects.select_for_update().get(pk=serializer.instance.pk)
            if locked.snapshot_at or locked.status not in {'draft', 'failed'}:
                raise ValidationError('This campaign is frozen. Create a new draft to change it.')
            instance = serializer.save(status='draft', last_error='')
            audit(self.request, 'campaign_update', campaign=instance.pk)


class RecipientCount(EmailBase, APIView):
    def post(self, request):
        serializer = RecipientCountSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        campaign = EmailCampaign(**serializer.validated_data)
        return Response({'count': len(recipients(campaign))})


class RecipientOptions(EmailBase, generics.ListAPIView):
    class Row(serializers.ModelSerializer):
        full_name = serializers.SerializerMethodField()
        class Meta:
            model = FormSubmission
            fields = ['id', 'reference_number', 'applicant_email', 'full_name']
        def get_full_name(self, obj): return context_for(obj)['full_name']
    serializer_class = Row
    def get_queryset(self):
        from registrations.review import review_queryset
        if not self.request.query_params.get('event'): raise ValidationError({'event': 'Choose an event.'})
        return review_queryset(self.request)


class CampaignAction(EmailBase, APIView):
    def post(self, request, pk, action):
        instance = get_object_or_404(scoped(EmailCampaign, request), pk=pk)
        if action == 'preview':
            choices = recipients(instance)
            context = context_for(choices[0][1]) if choices else example_context()
            subject, body, text = campaign_content(instance, choices[0][1], choices[0][0]) if choices else render(instance.subject, instance.html_content, instance.text_content, context)
            return Response({'recipient_count': len(choices), 'subject': subject, 'html_content': body, 'text_content': text})
        if action == 'test':
            if not request.user.email or not request.user.is_active:
                raise ValidationError('Set a verified administrator email on your account before sending a test.')
            from django.core.validators import validate_email
            validate_email(request.user.email)
            subject, body, text = render(instance.subject, instance.html_content, instance.text_content, example_context())
            key = request.data.get('request_key')
            try: key = str(uuid.UUID(str(key)))
            except (ValueError, TypeError): raise ValidationError({'request_key': 'Supply a unique UUID for this test attempt.'}) from None
            message, _ = EmailMessage.objects.get_or_create(event_key=f'test:{instance.pk}:{request.user.pk}:{key}', defaults={
                'event': instance.event, 'recipient_email': request.user.email.strip().casefold(), 'message_type': 'admin_test',
                'classification': 'operational', 'subject': f'[TEST] {subject}'[:255], 'html_content': body, 'text_content': text})
            audit(request, 'test_queue', message=str(message.pk))
            return Response({'id': message.pk, 'status': message.status}, status=202)
        if action not in {'send', 'schedule', 'pause', 'resume', 'cancel'}:
            raise ValidationError('Unsupported campaign action.')
        with transaction.atomic():
            instance = EmailCampaign.objects.select_for_update().get(pk=instance.pk)
            if action in {'send', 'schedule'}:
                if request.data.get('confirm') is not True:
                    raise ValidationError('Explicit confirmation is required before queueing recipients.')
                if instance.status != 'draft' or instance.snapshot_at:
                    raise ValidationError('Only a draft can be submitted once.')
                eligible = len(recipients(instance))
                if not eligible: raise ValidationError('No eligible recipients match this selection.')
                if action == 'schedule':
                    field = serializers.DateTimeField()
                    at = field.run_validation(request.data.get('scheduled_at'))
                    if at <= timezone.now(): raise ValidationError({'scheduled_at': 'Choose a future time.'})
                    instance.scheduled_at, instance.status = at, 'scheduled'
                else: instance.status = 'ready'
            elif action == 'pause':
                if instance.status not in {'sending', 'ready', 'scheduled'}: raise ValidationError('This campaign cannot be paused.')
                instance.status = 'paused'
            elif action == 'resume':
                if instance.status != 'paused': raise ValidationError('This campaign is not paused.')
                instance.status = 'sending' if instance.snapshot_at else ('scheduled' if instance.scheduled_at else 'ready')
            else:
                if instance.status in {'completed', 'cancelled'}: raise ValidationError('This campaign is already finished.')
                instance.status = 'cancelled'
            instance.save()
            audit(request, f'campaign_{action}', campaign=instance.pk)
        if action == 'cancel':
            # Release campaign lock before touching job rows, matching the worker lock order.
            instance.messages.filter(status__in=['pending', 'retry']).update(status='cancelled', last_error='Campaign cancelled before sending.')
        return Response(CampaignSerializer(instance).data, status=202)


class MessageList(EmailBase, generics.ListAPIView):
    serializer_class = MessageSerializer
    def get_queryset(self):
        rows = scoped(EmailMessage, self.request).select_related('event').prefetch_related('attempts')
        if self.request.query_params.get('attention') == '1':
            rows = rows.filter(status__in=['failed', 'unknown', 'hard_bounced', 'blocked', 'soft_bounced'])
        for key in ('status', 'event', 'campaign', 'submission'):
            value = self.request.query_params.get(key)
            if value:
                if key in {'event', 'campaign'} and (not value.isdecimal() or len(value) > 15): raise ValidationError({key: 'Expected a numeric ID.'})
                if key == 'submission':
                    try: uuid.UUID(value)
                    except ValueError: raise ValidationError({key: 'Invalid application ID.'}) from None
                rows = rows.filter(**{key: value})
        return rows


class MessageAction(EmailBase, APIView):
    def post(self, request, pk, action):
        with transaction.atomic():
            message = get_object_or_404(scoped(EmailMessage, request).select_for_update(), pk=pk)
            if request.data.get('confirm') is not True: raise ValidationError('Explicit confirmation is required.')
            if action == 'retry':
                if message.status != 'failed' or not message.retryable or message.redacted_at:
                    raise ValidationError('Only known failed retryable requests can be retried; accepted/uncertain outcomes must not be resent.')
                if message.campaign_id:
                    if message.campaign.status not in {'sending', 'completed'}: raise ValidationError('Resume the campaign first; cancelled campaigns cannot retry.')
                    EmailCampaign.objects.filter(pk=message.campaign_id, status='completed').update(status='sending', completed_at=None)
                if EmailPreference.objects.filter(email=message.recipient_email, suppressed=True).exists(): raise ValidationError('This address is suppressed.')
                message.status, message.retry_count, message.next_attempt_at = 'pending', 0, timezone.now()
            elif action == 'resolve':
                if message.status != 'unknown': raise ValidationError('Only uncertain outcomes need reconciliation.')
                resolution = request.data.get('resolution')
                if resolution == 'accepted':
                    provider_id = request.data.get('provider_message_id', '')
                    if not isinstance(provider_id, str) or not 1 <= len(provider_id) <= 500 or any(char in provider_id for char in '\r\n'):
                        raise ValidationError({'provider_message_id': 'Enter the original ID verified in Brevo logs.'})
                    message.status, message.provider_message_id, message.accepted_at = 'accepted', provider_id.strip('<>'), timezone.now()
                elif resolution == 'cancelled': message.status = 'cancelled'
                else: raise ValidationError('Choose accepted with provider proof, or cancelled. No resend is performed.')
            else: raise ValidationError('Unsupported action.')
            message.save()
            audit(request, f'message_{action}', message=str(message.pk))
        refresh_campaigns()
        return Response(MessageSerializer(message).data)


class EventSettings(EmailBase, APIView):
    def record(self, request, pk):
        event = get_object_or_404(scope_queryset(Event.objects.all(), request.user, 'pk'), pk=pk)
        if not can_manage_event(request.user, event.pk): raise PermissionDenied()
        return EventEmailSettings.objects.get_or_create(event=event, defaults={'status_notifications': STATUS_KEYS})[0]
    def get(self, request, pk): return Response(EventSettingsSerializer(self.record(request, pk)).data)
    def patch(self, request, pk):
        serializer = EventSettingsSerializer(self.record(request, pk), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request, 'settings_update', event=pk)
        return Response(serializer.data)


class Configuration(EmailBase, APIView):
    def get(self, request):
        return Response({'enabled': settings.EMAIL_ENABLED, 'provider': settings.EMAIL_PROVIDER, 'sender_email': settings.DEFAULT_FROM_EMAIL,
            'sender_name': settings.DEFAULT_FROM_NAME, 'configured': bool(settings.BREVO_API_KEY and settings.DEFAULT_FROM_EMAIL and settings.PUBLIC_SITE_URL and settings.PUBLIC_API_URL),
            'webhook_configured': bool(settings.BREVO_WEBHOOK_TOKEN), 'daily_limit': settings.EMAIL_DAILY_LIMIT,
            'transactional_reserve': settings.EMAIL_TRANSACTIONAL_RESERVE, 'retention_days': settings.EMAIL_RETENTION_DAYS,
            'variables': sorted(VARIABLES)})


class PreferenceUpdate(EmailBase, APIView):
    def post(self, request):
        submission_id = serializers.UUIDField().run_validation(request.data.get('submission'))
        submission = get_object_or_404(scoped(FormSubmission, request), pk=submission_id)
        enabled = request.data.get('marketing_opt_in')
        evidence = request.data.get('evidence', '')
        if type(enabled) is not bool or (enabled and (not isinstance(evidence, str) or not 5 <= len(evidence.strip()) <= 5000)):
            raise ValidationError('Record explicit consent evidence before enabling optional announcements.')
        pref, _ = EmailPreference.objects.get_or_create(email=submission.applicant_email.strip().casefold())
        pref.marketing_opt_in, pref.consent_evidence, pref.consent_recorded_by = enabled, evidence[:5000], request.user
        pref.unsubscribed_at = None if enabled else timezone.now()
        pref.save()
        audit(request, 'preference_update', submission=str(submission.pk), enabled=enabled)
        return Response({'marketing_opt_in': pref.marketing_opt_in, 'suppressed': pref.suppressed})


class SubmissionMail(PrivateStaffResponseMixin, APIView):
    permission_classes = [ApplicationReviewPermission]
    def get(self, request, pk):
        submission = get_object_or_404(scope_queryset(FormSubmission.objects.all(), request.user), pk=pk)
        payment = PaymentVerification.objects.filter(submission=submission).first()
        messages = EmailMessage.objects.filter(submission=submission).values('id', 'message_type', 'status', 'created_at', 'accepted_at', 'delivered_at')[:10]
        return Response({'payment': {'status': payment.status if payment else 'unpaid', 'amount': str(payment.amount) if payment and payment.amount is not None else '', 'currency': payment.currency if payment else 'BDT', 'verified_at': payment.verified_at if payment else None}, 'messages': list(messages)})


class PaymentSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['unpaid', 'pending', 'verified', 'rejected'])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'), allow_null=True, required=False)
    currency = serializers.RegexField(r'^[A-Z]{3}$', default='BDT')
    next_instructions = serializers.CharField(max_length=10000, required=False, allow_blank=True)


class VerifyPayment(EmailBase, APIView):
    def patch(self, request, pk):
        with transaction.atomic():
            submission = get_object_or_404(scoped(FormSubmission, request).select_for_update(), pk=pk)
            if not can_manage_event(request.user, submission.event_id): raise PermissionDenied()
            serializer = PaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            values = serializer.validated_data
            payment, _ = PaymentVerification.objects.get_or_create(submission=submission)
            old = payment.status
            if old == values['status']:
                if payment.amount != values.get('amount', payment.amount) or payment.currency != values['currency']:
                    raise ValidationError('Change the payment status before correcting verified payment details.')
                return Response({'status': payment.status})
            payment.status = values['status']
            payment.amount = values.get('amount', payment.amount)
            payment.currency = values['currency']
            payment.verified_at = timezone.now() if payment.status == 'verified' else None
            payment.verified_by = request.user if payment.status == 'verified' else None
            payment.save()
            details = {'payment_amount': f'{payment.currency} {payment.amount}' if payment.amount is not None else 'Not recorded', 'verified_at': payment.verified_at.isoformat() if payment.verified_at else '', 'next_instructions': values.get('next_instructions', '')}
            change = PaymentChange.objects.create(submission=submission, previous_status=old, status=payment.status, actor=request.user, details=details)
            audit(request, 'payment_update', submission=str(submission.pk), change=change.pk)
        return Response({'status': payment.status, 'verified_at': payment.verified_at})
