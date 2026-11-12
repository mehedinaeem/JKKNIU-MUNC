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
