import uuid
from rest_framework import serializers
from accounts.roles import can_manage_event
from events.models import Event
from forms.models import RegistrationForm
from registrations.models import FormSubmission
from .models import EmailTemplate, EmailCampaign, EmailMessage, EmailDeliveryAttempt, EventEmailSettings
from .notifications import STATUS_KEYS
from .rendering import validate_content


def permitted_event(request, event):
    from rest_framework.exceptions import PermissionDenied
    if not can_manage_event(request.user, event.pk):
        raise PermissionDenied('Email management is limited to assigned events.')


def recipient_filter(value, event):
    allowed = {'form_ids', 'statuses', 'form_types', 'payment_status', 'submission_ids', 'selection'}
    if not isinstance(value, dict) or set(value) - allowed:
        raise serializers.ValidationError('Unsupported recipient filter.')
    for key in ('form_ids', 'statuses', 'form_types', 'submission_ids'):
        if key in value and (not isinstance(value[key], list) or len(value[key]) > 500):
            raise serializers.ValidationError('Recipient selections must be bounded lists.')
    forms = value.get('form_ids', [])
    if any(type(item) is not int for item in forms) or RegistrationForm.objects.filter(event=event, pk__in=forms).count() != len(set(forms)):
        raise serializers.ValidationError('Choose registration forms belonging to this event.')
    if any(not isinstance(item, str) or item not in STATUS_KEYS for item in value.get('statuses', [])):
        raise serializers.ValidationError('Unknown application status.')
    types = value.get('form_types', [])
    if any(not isinstance(item, str) or len(item) > 100 for item in types) or set(types) - set(event.registration_forms.values_list('form_type', flat=True)):
        raise serializers.ValidationError('Choose existing form types for this event.')
    selection = value.get('selection', 'all')
    if selection not in {'all', 'custom'} or value.get('payment_status', '') not in {'', 'unpaid', 'verified'}:
        raise serializers.ValidationError('Invalid recipient selection.')
    ids = value.get('submission_ids', [])
    try: ids = [str(uuid.UUID(str(item))) for item in ids]
    except (ValueError, TypeError, AttributeError): raise serializers.ValidationError('Invalid application selection.') from None
    if selection == 'custom' and not ids:
        raise serializers.ValidationError('Select at least one application.')
    if ids and FormSubmission.objects.filter(event=event, pk__in=ids).count() != len(set(ids)):
        raise serializers.ValidationError('Choose applications belonging to this event.')
    return {**value, 'submission_ids': ids}


class ContentMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        current = self.instance
        event = attrs.get('event') or (current.event if current else None)
        if event:
            permitted_event(self.context['request'], event)
        if current and 'event' in attrs and attrs['event'] != current.event:
            raise serializers.ValidationError({'event': 'Create a new record to use a different event.'})
        subject = attrs.get('subject', current.subject if current else '')
        html = attrs.get('html_content', current.html_content if current else '')
        text = attrs.get('text_content', current.text_content if current else '')
        attrs['html_content'] = validate_content(subject, html, text)
        return attrs


class TemplateSerializer(ContentMixin, serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True, default='Global default')
    class Meta:
        model = EmailTemplate
        fields = ['id', 'name', 'template_key', 'event', 'event_title', 'subject', 'html_content', 'text_content', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        validators = []
        extra_kwargs = {'template_key': {'validators': []}, 'html_content': {'max_length': 150000}, 'text_content': {'max_length': 100000}}

    def validate(self, attrs):
        from accounts.roles import is_super_admin
        event = attrs.get('event', self.instance.event if self.instance else None)
        if not event and not is_super_admin(self.context['request'].user):
            raise serializers.ValidationError({'event': 'Only a Super Admin may edit global templates.'})
        attrs = super().validate(attrs)
        key = attrs.get('template_key', self.instance.template_key if self.instance else '')
        duplicate = EmailTemplate.objects.filter(event=event, template_key=key)
        if self.instance: duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists(): raise serializers.ValidationError({'template_key': 'This event/global scope already has a template with this key.'})
        return attrs


class CampaignSerializer(ContentMixin, serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    progress = serializers.SerializerMethodField()
    class Meta:
        model = EmailCampaign
        fields = ['id', 'name', 'event', 'event_title', 'subject', 'template', 'html_content', 'text_content', 'classification', 'recipient_filter', 'status', 'scheduled_at', 'created_by', 'created_at', 'started_at', 'completed_at', 'snapshot_at', 'last_error', 'progress']
        read_only_fields = ['status', 'scheduled_at', 'created_by', 'created_at', 'started_at', 'completed_at', 'snapshot_at', 'last_error']
        extra_kwargs = {'html_content': {'max_length': 150000}, 'text_content': {'max_length': 100000}, 'recipient_filter': {'required': False}}

    def validate(self, attrs):
        if self.instance and (self.instance.snapshot_at or self.instance.status not in {'draft', 'failed'}):
            raise serializers.ValidationError('Only unsent drafts may be edited. Cancel and create a new draft to change a frozen campaign.')
        attrs = super().validate(attrs)
        event = attrs.get('event') or self.instance.event
        template = attrs.get('template')
        if template and (not template.is_active or template.event_id not in {None, event.pk}):
            raise serializers.ValidationError({'template': 'Choose an active template for this event or a global default.'})
        attrs['recipient_filter'] = recipient_filter(attrs.get('recipient_filter', self.instance.recipient_filter if self.instance else {}), event)
        return attrs

    def get_progress(self, obj):
        from django.db.models import Count
        return dict(obj.messages.values('status').annotate(total=Count('pk')).values_list('status', 'total'))


class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailDeliveryAttempt
        fields = ['number', 'outcome', 'http_status', 'detail', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    attempts = AttemptSerializer(many=True, read_only=True)
    can_retry = serializers.SerializerMethodField()
    class Meta:
        model = EmailMessage
        fields = ['id', 'recipient_email', 'event', 'event_title', 'submission', 'campaign', 'message_type', 'subject', 'provider', 'provider_message_id', 'status', 'attempt_count', 'next_attempt_at', 'accepted_at', 'delivered_at', 'last_error', 'created_at', 'updated_at', 'attempts', 'can_retry']
        read_only_fields = fields

    def get_can_retry(self, obj):
        return obj.status == 'failed' and obj.retryable and obj.redacted_at is None


class EventSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventEmailSettings
        fields = ['event', 'registration_enabled', 'payment_enabled', 'status_notifications', 'next_instructions', 'status_instructions', 'updated_at']
        read_only_fields = ['event', 'updated_at']
        extra_kwargs = {'next_instructions': {'max_length': 10000}}

    def validate_status_notifications(self, value):
        if not isinstance(value, list) or any(not isinstance(item, str) or item not in STATUS_KEYS for item in value):
            raise serializers.ValidationError('Choose supported application statuses.')
        return list(dict.fromkeys(value))

    def validate_status_instructions(self, value):
        if not isinstance(value, dict) or set(value) - set(STATUS_KEYS) or any(not isinstance(item, str) or len(item) > 10000 for item in value.values()):
            raise serializers.ValidationError('Use supported statuses and text instructions of at most 10,000 characters.')
        return value


class RecipientCountSerializer(serializers.Serializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    classification = serializers.ChoiceField(choices=['operational', 'marketing'], default='operational')
    recipient_filter = serializers.JSONField(default=dict)
    def validate(self, attrs):
        permitted_event(self.context['request'], attrs['event'])
        attrs['recipient_filter'] = recipient_filter(attrs['recipient_filter'], attrs['event'])
        return attrs


class PreviewContentSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    html_content = serializers.CharField(max_length=150000, allow_blank=True)
    text_content = serializers.CharField(max_length=100000)
