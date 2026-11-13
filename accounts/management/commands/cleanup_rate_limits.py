from django.core.management.base import BaseCommand, CommandError
from accounts.models import RateLimitCounter
from accounts.rate_limits import database_now


class Command(BaseCommand):
    help = 'Delete expired quota counters in bounded batches; active counters are preserved.'
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10000)
        parser.add_argument('--dry-run', action='store_true')
    def handle(self, *args, **options):
        if not 1 <= options['limit'] <= 100000:
            raise CommandError('--limit must be between 1 and 100000.')
        try:
            cutoff = database_now()
            keys = list(RateLimitCounter.objects.filter(expires_at__lte=cutoff).order_by('expires_at').values_list('pk', flat=True)[:options['limit']])
            if options['dry_run']:
                self.stdout.write(f'Expired counters eligible in this batch: {len(keys)}; no changes made.')
            else:
                count, _ = RateLimitCounter.objects.filter(pk__in=keys, expires_at__lte=cutoff).delete()
                self.stdout.write(f'Deleted {count} expired counters.')
        except Exception:
            raise CommandError('Rate-limit cleanup failed. Check database availability.') from None
