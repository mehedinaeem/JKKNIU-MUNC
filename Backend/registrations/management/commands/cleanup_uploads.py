from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from registrations.models import UploadCleanup
from registrations.services import cleanup_intent


class Command(BaseCommand):
    help = 'Retry abandoned private upload cleanup; never delete committed file references.'

    def add_arguments(self, parser):
        parser.add_argument('--min-age-seconds', type=int, default=3600)
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if options['min_age_seconds'] < 300 or not 1 <= options['limit'] <= 500:
            raise CommandError('Minimum age must be at least 300 seconds and limit must be 1–500.')
        cutoff = timezone.now() - timedelta(seconds=options['min_age_seconds'])
        ids = list(UploadCleanup.objects.filter(created_at__lt=cutoff).order_by('pk').values_list('pk', flat=True)[:options['limit']])
        cleared = 0
        for pk in ids:
            with transaction.atomic():
                query = UploadCleanup.objects.filter(pk=pk)
                query = query.select_for_update(skip_locked=True) if connection.features.has_select_for_update_skip_locked else query.select_for_update()
                intent = query.first()
                if intent is not None and cleanup_intent(intent):
                    cleared += 1
        self.stdout.write(f'Cleared {cleared} cleanup intents.')
