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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(opens_at__isnull=True) | Q(closes_at__isnull=True) | Q(closes_at__gte=F("opens_at")), name="form_window_order"),
            models.CheckConstraint(condition=Q(capacity__isnull=True) | Q(capacity__gte=1), name="form_capacity_positive"),
        ]

    def clean(self):
        super().clean()
        validate_window(self, "opens_at", "closes_at")
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError({"capacity": "Must be at least one or null for unlimited."})

    def __str__(self):
        return self.title
