from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Event


class ModelCleanMixin:
    """Validate merged values so PATCH cannot bypass cross-field rules."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        model = self.Meta.model
        values = {field.name: getattr(self.instance, field.name) for field in model._meta.fields} if self.instance else {}
        values.update(attrs)
        candidate = model(**values)
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class EventSerializer(ModelCleanMixin, serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "slug", "short_description", "description", "event_type",
                  "venue", "start_date", "end_date", "registration_start", "registration_end",
                  "status", "cover_image", "organizer", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EventQuerySerializer(serializers.Serializer):
    event_type = serializers.CharField(required=False, max_length=100)
    search = serializers.CharField(required=False, max_length=200, allow_blank=True)
    start_date_after = serializers.DateTimeField(required=False)
    start_date_before = serializers.DateTimeField(required=False)
    ordering = serializers.ChoiceField(required=False, choices=[
        "start_date", "-start_date", "created_at", "-created_at", "title", "-title",
    ])
