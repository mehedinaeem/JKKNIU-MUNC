import uuid
from django.conf import settings
from django.db import models
from django.core.files.storage import FileSystemStorage, storages
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateUploadStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.BASE_DIR / "private_uploads", base_url=None)

    def url(self, name):
        raise NotImplementedError("Private uploads require authenticated download.")


def private_upload_storage():
    return storages["private_uploads"]


def upload_path(instance, filename):
    from pathlib import Path
    return f"answers/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"



def public_reference():
    return f"JM-{uuid.uuid4().hex.upper()}"


class FormSubmission(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under review'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        WAITLISTED = 'waitlisted', 'Waitlisted'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=40, unique=True, default=public_reference, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.PROTECT, related_name='form_submissions')
    registration_form = models.ForeignKey('club_forms.RegistrationForm', on_delete=models.PROTECT, related_name='submissions')
    form_version = models.ForeignKey('club_forms.FormVersion', on_delete=models.PROTECT, related_name='submissions')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    # Blank is retained only for historical submissions with no recorded email.
    applicant_email = models.EmailField(blank=True)
    answers = models.JSONField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at', '-id']
        indexes = [models.Index(fields=['registration_form', 'applicant_email'], name='submission_form_email_idx')]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.form_version_id and self.registration_form_id:
            if self.form_version.form_id != self.registration_form_id:
                raise ValidationError({'form_version': 'Version must belong to the registration form.'})
        if self.registration_form_id and self.event_id:
            if self.registration_form.event_id != self.event_id:
                raise ValidationError({'event': 'Event must match the registration form.'})
        self.applicant_email = self.applicant_email.strip().casefold()

    @property
    def version(self):
        return self.form_version

    @property
    def version_id(self):
        return self.form_version_id

    @property
    def created_at(self):
        return self.submitted_at


# Import compatibility for callers of the previous internal model name.
Submission = FormSubmission


class SubmissionFile(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='files')
    field_key = models.SlugField(max_length=100)
    storage_provider = models.CharField(max_length=30, default='legacy_local')
    provider_file_id = models.CharField(max_length=500, blank=True)
    original_filename = models.CharField(max_length=180, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    # Kept only to preserve access to historical Part 3 local files.
    file = models.FileField(storage=private_upload_storage, upload_to=upload_path, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['submission', 'field_key'], name='one_file_per_submission_field')]


class UploadCleanup(models.Model):
    """Durable upload intents; removed in the same DB commit that links a file."""
    storage_provider = models.CharField(max_length=30)
    provider_file_id = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)


class SubmissionStatusChange(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.PROTECT, related_name='status_changes')
    previous_status = models.CharField(max_length=15)
    status = models.CharField(max_length=15)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
