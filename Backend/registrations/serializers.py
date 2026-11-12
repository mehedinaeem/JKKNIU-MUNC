from django.urls import reverse
from rest_framework import serializers
from .models import FormSubmission, SubmissionFile


class PublicSubmissionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    applicant_email = serializers.EmailField(max_length=254)
    answers = serializers.JSONField()

    def validate(self, attrs):
        if set(self.initial_data) - {'version', 'applicant_email', 'answers'}:
            raise serializers.ValidationError('Unexpected submission properties.')
        return attrs

    def validate_applicant_email(self, value):
        return value.strip().casefold()


class SubmissionFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionFile
        fields = ['id', 'field_key', 'original_filename', 'content_type', 'file_size', 'created_at', 'download_url']
        read_only_fields = fields

    def get_download_url(self, obj):
        return reverse('forms:file-download', kwargs={'pk': obj.pk})


class SubmissionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmission
        # Applicant PII/answers appear only in the authorized staff detail view.
        fields = ['id', 'reference_number', 'event', 'registration_form', 'form_version',
                  'status', 'submitted_at', 'updated_at']
        read_only_fields = fields


class SubmissionDetailSerializer(SubmissionSummarySerializer):
    form_schema = serializers.JSONField(source='form_version.schema', read_only=True)
    files = SubmissionFileSerializer(many=True, read_only=True)

    class Meta(SubmissionSummarySerializer.Meta):
        fields = SubmissionSummarySerializer.Meta.fields + ['applicant_email', 'answers', 'files', 'form_schema']
        read_only_fields = fields


class SubmissionStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FormSubmission.Status.choices)

    def validate(self, attrs):
        if set(self.initial_data) != {'status'}:
            raise serializers.ValidationError('Only status can be changed through this endpoint.')
        return attrs
