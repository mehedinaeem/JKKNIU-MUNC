from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


def validate_window(instance, start, end):
    first, last = getattr(instance, start), getattr(instance, end)
    if first and last and last < first:
        raise ValidationError({end: f"Must be on or after {start}."})


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=100)
    venue = models.CharField(max_length=255, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    registration_start = models.DateTimeField(null=True, blank=True)
    registration_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    # Reference only: no uploads and no copying of frontend archive images.
    cover_image = models.URLField(max_length=1000, blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name="organized_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")), name="event_date_order"),
            models.CheckConstraint(condition=Q(registration_start__isnull=True) | Q(registration_end__isnull=True) | Q(registration_end__gte=F("registration_start")), name="event_registration_order"),
        ]

    def clean(self):
        super().clean()
        validate_window(self, "start_date", "end_date")
        validate_window(self, "registration_start", "registration_end")

    def __str__(self):
        return self.title
