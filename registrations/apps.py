from django.apps import AppConfig


class RegistrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registrations"
    label = "registrations"

    def ready(self):
        from . import checks  # Register deployment validation.
