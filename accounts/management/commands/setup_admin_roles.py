from django.core.management.base import BaseCommand
from accounts.roles import setup_roles


class Command(BaseCommand):
    help = 'Idempotently synchronize administrator groups and their Django model permissions; never creates users.'

    def handle(self, *args, **options):
        setup_roles()
        self.stdout.write(self.style.SUCCESS('Administrator groups and permissions synchronized. No user assignments changed.'))
