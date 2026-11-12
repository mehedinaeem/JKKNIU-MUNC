from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import FormField, FormVersion, RegistrationForm
from .validation import validate_answers


FIELD_ATTRIBUTES = ('key', 'field_type', 'label', 'help_text', 'placeholder', 'required',
                    'display_order', 'default_value', 'validation', 'options',
                    'allowed_extensions', 'max_file_size')


def draft_schema(form):
    return {'title': form.title, 'description': form.description, 'form_type': form.form_type,
            'fields': [{name: getattr(field, name) for name in FIELD_ATTRIBUTES}
                       for field in form.fields.order_by('display_order', 'id')]}


@transaction.atomic
def save_draft(serializer):
    data = dict(serializer.validated_data)
    fields = data.pop('fields', None)
    if serializer.instance:
        form = RegistrationForm.objects.select_for_update().get(pk=serializer.instance.pk)
        for key, value in data.items():
            setattr(form, key, value)
        form.save()
    else:
        form = RegistrationForm.objects.create(**data)
    if fields is not None:
        keys = [field['key'] for field in fields]
        form.fields.exclude(key__in=keys).delete()
        for values in fields:
            values = dict(values)
            key = values.pop('key')
            FormField.objects.update_or_create(form=form, key=key, defaults=values)
    return form


@transaction.atomic
def publish_form(form_id):
    form = RegistrationForm.objects.select_for_update().get(pk=form_id)
    schema = draft_schema(form)
    from .serializers import FormFieldSerializer
    if len(schema['fields']) > 100:
        raise ValidationError({'fields': 'At most 100 fields are supported.'})
    if not schema['fields']:
        raise ValidationError({'fields': 'Add at least one field before publishing.'})
    validator = FormFieldSerializer(data=schema['fields'], many=True)
    validator.is_valid(raise_exception=True)
    from django.core.exceptions import ValidationError as ModelValidationError
    try:
        form.full_clean()
    except ModelValidationError as exc:
        raise ValidationError(exc.message_dict) from exc
    number = (form.versions.aggregate(last=Max('number'))['last'] or 0) + 1
    version = FormVersion.objects.create(form=form, number=number, schema=schema)
    form.status = RegistrationForm.Status.PUBLISHED
    form.save(update_fields=['status', 'updated_at'])
    return version


@transaction.atomic
def duplicate_form(form_id, title, slug):
    source = RegistrationForm.objects.select_for_update().get(pk=form_id)
    clone = RegistrationForm.objects.create(event=source.event, title=title, slug=slug,
        description=source.description, form_type=source.form_type, opens_at=source.opens_at,
        closes_at=source.closes_at, capacity=source.capacity,
        allow_multiple_submissions=source.allow_multiple_submissions)
    for field in source.fields.all():
        FormField.objects.create(form=clone, **{name: getattr(field, name) for name in FIELD_ATTRIBUTES})
    return clone


def availability_error(form, now=None):
    now = now or timezone.now()
    event = form.event
    if event.status != 'published' or form.status != 'published' or not form.versions.exists():
        return 'This form is not published.'
    if event.registration_start and now < event.registration_start or form.opens_at and now < form.opens_at:
        return 'Registration has not opened.'
    if (now >= event.start_date or event.registration_end and now >= event.registration_end
            or form.closes_at and now >= form.closes_at):
        return 'Registration has closed.'
    if form.capacity is not None and form.submission_count >= form.capacity:
        return 'This form has reached capacity.'
    return None


@transaction.atomic
def submit_form(form_id, user, version_number, answers, files=None):
    # Serializing on the form prevents both over-capacity and duplicate concurrent submissions.
    form = RegistrationForm.objects.select_for_update().select_related('event').get(pk=form_id)
    from events.models import Event
    form.event = Event.objects.select_for_update().get(pk=form.event_id)
    error = availability_error(form)
    if error:
        raise ValidationError({'form': error})
    version = form.versions.first()
    if version.number != version_number:
        raise ValidationError({'version': 'The form has changed. Reload the published form.'})
    from registrations.models import Submission, SubmissionFile
    if not form.allow_multiple_submissions and Submission.objects.filter(version__form=form, submitted_by=user).exists():
        raise ValidationError({'form': 'You have already submitted this form.'})
    clean, uploads = validate_answers(version.schema, answers, files)
    if sum(upload.size for upload in uploads.values()) > 20 * 1024 * 1024:
        raise ValidationError({'files': 'Total file size cannot exceed 20 MiB.'})
    # Local private storage is development-only; fail closed until durable private storage is configured.
    from django.conf import settings
    from django.core.files.storage import FileSystemStorage, storages
    if uploads and not settings.DEBUG and isinstance(storages['private_uploads'], FileSystemStorage):
        raise ValidationError({'files': 'File submissions require durable private storage configuration before production use.'})
    # A conditional write also guards capacity when using SQLite, which has no row locks.
    from django.db.models import F, Q
    claimed = RegistrationForm.objects.filter(pk=form.pk).filter(
        Q(capacity__isnull=True) | Q(submission_count__lt=F('capacity'))
    ).update(submission_count=F('submission_count') + 1)
    if not claimed:
        raise ValidationError({'form': 'This form has reached capacity.'})
    submission = Submission.objects.create(version=version, submitted_by=user, answers=clean)
    saved_files = []
    try:
        for key, upload in uploads.items():
            item = SubmissionFile(submission=submission, field_key=key)
            item.file.save(upload.name, upload, save=False)
            saved_files.append(item.file)
            item.save()
    except Exception:
        for stored in saved_files:
            stored.delete(save=False)
        raise
    return submission
