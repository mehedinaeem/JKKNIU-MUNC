from datetime import datetime, timezone
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from events.models import Event
from forms.models import RegistrationForm


class Command(BaseCommand):
    help = "Explicitly add fictional development events/forms; never reads the frontend archive."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is restricted to DEBUG=True.")
        event, created = Event.objects.get_or_create(slug="demo-national-mun-2027", defaults={
            "title": "Demo National MUN Conference 2027", "event_type": "conference",
            "description": "Fictional development sample, not an announced club event.",
            "start_date": datetime(2027, 3, 1, 3, tzinfo=timezone.utc),
            "end_date": datetime(2027, 3, 3, 12, tzinfo=timezone.utc),
            "status": Event.Status.PUBLISHED,
        })
        for title, kind in [("Delegate Registration", "delegate"),
                            ("Executive Board Application", "executive-board"),
                            ("Secretariat Recruitment", "secretariat"),
                            ("Campus Ambassador Application", "campus-ambassador")]:
            RegistrationForm.objects.get_or_create(slug=f"demo-2027-{kind}", defaults={
                "event": event, "title": title, "form_type": kind,
                "description": "Fictional demo form. Custom form types are supported.",
            })
        self.stdout.write(self.style.SUCCESS("Demo event/forms available; existing records were not overwritten."))
