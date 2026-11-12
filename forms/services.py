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
    from django.conf import settings
    if sum(field['field_type'] == 'file' and field['required'] for field in schema['fields']) > settings.DATA_UPLOAD_MAX_NUMBER_FILES:
        raise ValidationError({'fields': 'Required file fields exceed the supported files per submission.'})
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
def duplicate_form(form_id, title, slug, event=None):
    source = RegistrationForm.objects.select_for_update().get(pk=form_id)
    clone = RegistrationForm.objects.create(event=event or source.event, title=title, slug=slug,
        description=source.description, form_type=source.form_type, opens_at=source.opens_at if event is None or event.pk == source.event_id else None,
        closes_at=source.closes_at if event is None or event.pk == source.event_id else None, capacity=source.capacity,
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


def submit_form(form_id, user, version_number, answers, files=None):
    """Compatibility entry point for the existing authenticated submission API."""
    from registrations.services import submit_application
    return submit_application(form_id, user.email, version_number, answers, files, user=user)
