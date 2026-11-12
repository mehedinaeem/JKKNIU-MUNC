from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from events.models import validate_window


class RegistrationForm(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="registration_forms")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    form_type = models.CharField(max_length=100, help_text="Custom type chosen by the administrator.")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Blank means unlimited; otherwise at least one.")
    allow_multiple_submissions = models.BooleanField(default=False)
    submission_count = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(opens_at__isnull=True) | Q(closes_at__isnull=True) | Q(closes_at__gte=F("opens_at")), name="form_window_order"),
            models.CheckConstraint(condition=Q(capacity__isnull=True) | Q(capacity__gte=1), name="form_capacity_positive"),
        ]

    def save(self, *args, **kwargs):
        # Only the transactional submission service updates this counter via an atomic query.
        # Saving an older model instance must never overwrite a newly accepted submission.
        if self.pk and kwargs.get('update_fields') is None:
            kwargs['update_fields'] = [field.name for field in self._meta.concrete_fields
                                      if not field.primary_key and field.name not in {'submission_count', 'created_at'}]
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        validate_window(self, "opens_at", "closes_at")
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError({"capacity": "Must be at least one or null for unlimited."})

    def __str__(self):
        return self.title


class FormField(models.Model):
    class Type(models.TextChoices):
        SHORT_TEXT = "short_text", "Short text"
        LONG_TEXT = "long_text", "Long text"
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone number"
        INTEGER = "integer", "Integer"
        DECIMAL = "decimal", "Decimal"
        DATE = "date", "Date"
        DROPDOWN = "dropdown", "Dropdown"
        RADIO = "radio", "Radio buttons"
        CHECKBOXES = "checkboxes", "Checkboxes"
        FILE = "file", "File upload"
        URL = "url", "URL"
        CONSENT = "consent", "Consent checkbox"

    form = models.ForeignKey(RegistrationForm, related_name="fields", on_delete=models.CASCADE)
    key = models.SlugField(max_length=100)
    field_type = models.CharField(max_length=20, choices=Type.choices)
    label = models.CharField(max_length=255)
    help_text = models.TextField(blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    default_value = models.JSONField(null=True, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    # Choices are declarative objects: {"value": "stable-value", "label": "Visible label"}.
    options = models.JSONField(default=list, blank=True)
    allowed_extensions = models.JSONField(default=list, blank=True)
    max_file_size = models.PositiveIntegerField(null=True, blank=True, help_text="Bytes")

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [models.UniqueConstraint(fields=["form", "key"], name="unique_form_field_key")]

    def clean(self):
        from .validation import validate_field_definition
        from rest_framework.exceptions import ValidationError as APIValidationError
        try:
            validate_field_definition({name: getattr(self, name) for name in (
                "key", "field_type", "label", "help_text", "placeholder", "required",
                "display_order", "default_value", "validation", "options", "allowed_extensions", "max_file_size")})
        except APIValidationError as exc:
            raise ValidationError({"validation": str(exc.detail)}) from exc

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            if original.key != self.key or original.form_id != self.form_id:
                raise ValidationError("Existing field keys and parent forms are immutable.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.key}: {self.label}"


class ImmutableVersionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Published versions cannot be changed.")

    def delete(self):
        raise ValidationError("Published versions cannot be deleted.")


class FormVersion(models.Model):
    form = models.ForeignKey(RegistrationForm, related_name="versions", on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    schema = models.JSONField()
    published_at = models.DateTimeField(auto_now_add=True)
    objects = ImmutableVersionQuerySet.as_manager()

    class Meta:
        ordering = ["-number"]
        constraints = [models.UniqueConstraint(fields=["form", "number"], name="unique_form_version")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Published versions cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Published versions cannot be deleted.")

    def __str__(self):
        return f"{self.form} v{self.number}"
