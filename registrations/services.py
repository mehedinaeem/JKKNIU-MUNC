import logging
import hashlib
import json
import hmac
from pathlib import Path
import uuid

from django.db import transaction
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError

from forms.models import RegistrationForm
from forms.services import availability_error
from forms.validation import validate_answers
from .models import FormSubmission, SubmissionFile, UploadCleanup, SubmissionStatusChange
from .storage import get_provider
from .throttles import SubmissionUnavailable

logger = logging.getLogger(__name__)


def cleanup_intent(intent):
    """Never delete an asset already linked to a committed submission."""
    if SubmissionFile.objects.filter(storage_provider=intent.storage_provider,
                                     provider_file_id=intent.provider_file_id).exists():
        intent.delete()
        return True
    try:
        get_provider(intent.storage_provider).delete(intent.provider_file_id)
    except Exception:
        UploadCleanup.objects.filter(pk=intent.pk).update(attempts=F('attempts') + 1)
        logger.warning('Private upload cleanup deferred; intent=%s', intent.pk)
        return False
    intent.delete()
    return True


def check_version(form, version_number):
    error = availability_error(form)
    if error:
        raise ValidationError({'form': error})
    version = form.versions.first()
    if version.number != version_number:
        raise ValidationError({'version': 'The form has changed. Reload it before submitting.'})
    return version


def request_digest(email, version, answers, files):
    try:
        digest = hashlib.sha256(json.dumps({'email': email, 'version': version, 'answers': answers},
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    except (ValueError, TypeError):
        raise ValidationError({'answers': 'Invalid answer data.'}) from None
    total = 0
    for key, upload in sorted((files or {}).items()):
        if not hasattr(upload, 'chunks') or upload.size > 10 * 1024 * 1024:
            raise ValidationError({'files': 'Unsupported file or file size.'})
        total += upload.size
        if total > 20 * 1024 * 1024:
            raise ValidationError({'files': 'Total upload size cannot exceed 20 MiB.'})
        digest.update(json.dumps([key, upload.name, upload.content_type, upload.size]).encode())
        upload.seek(0)
        for chunk in upload.chunks():
            digest.update(chunk)
        upload.seek(0)
    return digest.hexdigest()


def existing_submission(form_id, key, digest):
    if key is None:
        return None
    prior = FormSubmission.objects.filter(registration_form_id=form_id, submission_key=key).first()
    if prior and not hmac.compare_digest(prior.submission_digest, digest):
        raise ValidationError({'submission_key': 'This attempt does not match the earlier application. Retry the original answers and files, or contact the organisers.'})
    return prior


def submit_application(form_id, applicant_email, version_number, answers, files=None, user=None, submission_key=None):
    """Own the transaction boundary so upload cleanup also catches commit failures."""
    applicant_email = applicant_email.strip().casefold()
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError as ModelValidationError
    try:
        validate_email(applicant_email)
    except ModelValidationError:
        raise ValidationError({'applicant_email': 'Enter a valid email address.'}) from None
    fingerprint = request_digest(applicant_email, version_number, answers, files) if submission_key else ''
    prior = existing_submission(form_id, submission_key, fingerprint)
    if prior:
        return prior
    preliminary = RegistrationForm.objects.select_related('event').get(pk=form_id)
    try:
        version = check_version(preliminary, version_number)
        clean, uploads = validate_answers(version.schema, answers, files)
    except ValidationError:
        # Recover a concurrent commit that completed after the first receipt check.
        prior = existing_submission(form_id, submission_key, fingerprint)
        if prior:
            return prior
        raise
    if sum(upload.size for upload in uploads.values()) > 20 * 1024 * 1024:
        raise ValidationError({'files': 'Total upload size cannot exceed 20 MiB.'})
    provider = None
    intents, attempted = {}, set()
    try:
        if uploads:
            provider = get_provider()
            for key, upload in uploads.items():
                file_id = f'applications/{uuid.uuid4().hex}{Path(upload.name).suffix.lower()}'
                # Intents precede both the DB admission transaction and the remote upload.
                # A crash leaves a retryable task, not an untracked remote file.
                intents[key] = UploadCleanup.objects.create(storage_provider=provider.name, provider_file_id=file_id)
        with transaction.atomic():
            list(UploadCleanup.objects.select_for_update().filter(pk__in=[item.pk for item in intents.values()]).order_by('pk'))
            form = RegistrationForm.objects.select_for_update().get(pk=form_id)
            from events.models import Event
            form.event = Event.objects.select_for_update().get(pk=form.event_id)
            prior = existing_submission(form_id, submission_key, fingerprint)
            if prior:
                # A concurrent identical request committed while we were validating.
                for intent in intents.values():
                    UploadCleanup.objects.filter(pk=intent.pk).delete()
                return prior
            version = check_version(form, version_number)
            # Validate against the locked current snapshot, not a mutable draft.
            clean, validated_uploads = validate_answers(version.schema, answers, files)
            duplicates = FormSubmission.objects.filter(registration_form=form, applicant_email=applicant_email)
            if user is not None and user.is_authenticated:
                duplicates = FormSubmission.objects.filter(registration_form=form).filter(
                    Q(applicant_email=applicant_email) | Q(submitted_by=user))
            if not form.allow_multiple_submissions and duplicates.exists():
                # Do not confirm identities, references, status or any previous answers.
                raise ValidationError({'form': 'This application cannot be accepted.'})
            claimed = RegistrationForm.objects.filter(pk=form.pk).filter(
                Q(capacity__isnull=True) | Q(submission_count__lt=F('capacity'))
            ).update(submission_count=F('submission_count') + 1)
            if not claimed:
                raise ValidationError({'form': 'This form is not accepting more submissions.'})
            submission = FormSubmission.objects.create(event=form.event, registration_form=form,
                form_version=version, applicant_email=applicant_email, answers=clean,
                submission_key=submission_key, submission_digest=fingerprint,
                submitted_by=user if user is not None and user.is_authenticated else None)
            for key, upload in validated_uploads.items():
                intent = intents[key]
                attempted.add(key)  # A timeout may mean the upload succeeded remotely.
                provider.upload(intent.provider_file_id, upload)
                SubmissionFile.objects.create(submission=submission, field_key=key,
                    storage_provider=provider.name, provider_file_id=intent.provider_file_id,
                    original_filename=upload.name, content_type=upload.content_type, file_size=upload.size)
                UploadCleanup.objects.filter(pk=intent.pk).delete()
        return submission
    except Exception as exc:
        # This runs after transaction.atomic has rolled back, including commit failures.
        for key, intent in intents.items():
            try:
                if key in attempted:
                    cleanup_intent(intent)
                else:
                    intent.delete()
            except Exception:
                logger.warning('Private upload cleanup requires retry; intent=%s', intent.pk)
        if isinstance(exc, ValidationError):
            raise
        raise SubmissionUnavailable() from None


@transaction.atomic
def change_status(submission_id, status, actor):
    submission = FormSubmission.objects.select_for_update().get(pk=submission_id)
    if submission.status != status:
        SubmissionStatusChange.objects.create(submission=submission, previous_status=submission.status,
                                               status=status, changed_by=actor)
        submission.status = status
        submission.save(update_fields=['status', 'updated_at'])
    return submission
