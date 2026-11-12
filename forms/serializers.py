from rest_framework import serializers
from events.serializers import ModelCleanMixin
from .models import RegistrationForm


class RegistrationFormSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = RegistrationForm
        fields = ["id", "event", "title", "slug", "description", "form_type", "status",
                  "opens_at", "closes_at", "capacity", "allow_multiple_submissions",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import FormField
        model = FormField
        fields = ['key', 'field_type', 'label', 'help_text', 'placeholder', 'required',
                  'display_order', 'default_value', 'validation', 'options',
                  'allowed_extensions', 'max_file_size']
        extra_kwargs = {
            'help_text': {'max_length': 10000, 'default': ''},
            'placeholder': {'default': ''}, 'required': {'default': False},
            'display_order': {'default': 0},
            'validation': {'default': dict}, 'options': {'default': list},
            'allowed_extensions': {'default': list},
            'default_value': {'default': None}, 'max_file_size': {'default': None},
        }

    def validate(self, attrs):
        from .validation import validate_field_definition
        missing = [name for name in ('key', 'field_type', 'label') if name not in attrs]
        if missing:
            raise serializers.ValidationError({name: 'Required in every complete field definition.' for name in missing})
        attrs = {'help_text': '', 'placeholder': '', 'required': False, 'display_order': 0,
                 'default_value': None, 'validation': {}, 'options': [],
                 'allowed_extensions': [], 'max_file_size': None, **attrs}
        return validate_field_definition(attrs)


class DraftFormSerializer(RegistrationFormSerializer):
    fields = FormFieldSerializer(many=True, required=False)

    class Meta(RegistrationFormSerializer.Meta):
        fields = RegistrationFormSerializer.Meta.fields + ['fields']

    def validate(self, attrs):
        fields = attrs.pop('fields', None)
        request = self.context.get('request')
        event = attrs.get('event') or (self.instance.event if self.instance else None)
        if request and event:
            from accounts.roles import can_manage_event
            from rest_framework.exceptions import PermissionDenied
            permission = 'club_forms.change_registrationform' if self.instance else 'club_forms.add_registrationform'
            if not can_manage_event(request.user, event.pk, permission):
                raise PermissionDenied('You cannot manage forms for this event.')
        attrs = super().validate(attrs)
        if attrs.get('status') == 'published':
            raise serializers.ValidationError({'status': 'Use the publish endpoint to publish a version.'})
        if self.instance and 'event' in attrs and attrs['event'].pk != self.instance.event_id:
            raise serializers.ValidationError({'event': 'An existing form cannot be moved to another event.'})
        if fields is not None:
            from .validation import MAX_FIELDS
            keys = [field['key'] for field in fields]
            if len(keys) != len(set(keys)):
                raise serializers.ValidationError({'fields': 'Field keys must be unique within the form.'})
            if len(fields) > MAX_FIELDS:
                raise serializers.ValidationError({'fields': 'At most 100 fields are supported.'})
            attrs['fields'] = fields
        return attrs

    def create(self, validated_data):
        from .services import save_draft
        from django.db import IntegrityError
        try:
            return save_draft(self)
        except IntegrityError as exc:
            raise serializers.ValidationError({'slug': 'A conflicting form or field already exists.'}) from exc

    def update(self, instance, validated_data):
        from .services import save_draft
        from django.db import IntegrityError
        try:
            return save_draft(self)
        except IntegrityError as exc:
            raise serializers.ValidationError({'slug': 'A conflicting form or field already exists.'}) from exc


class DuplicateFormSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=255)

    def validate_slug(self, value):
        if RegistrationForm.objects.filter(slug=value).exists():
            raise serializers.ValidationError('This slug is already in use.')
        return value


class SubmissionInputSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    answers = serializers.JSONField()
