from django.core.management.base import BaseCommand, CommandError
from mailing.queue import process


class Command(BaseCommand):
    help = 'Process the durable email queue. Never resend uncertain outcomes automatically.'
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--transactional-only', action='store_true')
    def handle(self, *args, **options):
        if not 1 <= options['limit'] <= 1000: raise CommandError('--limit must be between 1 and 1000.')
        try:
            result = process(options['limit'], options['transactional_only'], options['dry_run'])
        except Exception:
            raise CommandError('Email queue batch failed. Durable jobs are retained; inspect database readiness and reconcile any in-flight outcomes.') from None
        self.stdout.write(str(result))
