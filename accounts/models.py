from django.conf import settings
from django.db import models


class EventAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_assignments')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='admin_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'event'], name='unique_administrator_event')]

    def __str__(self):
        return f'{self.user} — {self.event}'
