import time
import logging
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from mailing.queue import process


class Command(BaseCommand):
    help = 'Run a dedicated polling email worker. Requires a funded worker dyno in production.'
    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                try:
                    process(limit=50)
                except Exception:
                    logging.getLogger(__name__).warning('Email queue worker could not complete a batch; jobs remain durable.')
                    time.sleep(10)
                time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write('Worker stopped.')
