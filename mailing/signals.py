"""Post-commit notification hooks; the worker reconciles missed queue insertions."""
import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from registrations.models import FormSubmission, SubmissionStatusChange
from .models import PaymentChange
logger = logging.getLogger(__name__)


def after_commit(kind, pk):
    def queue():
        try:
            from .notifications import queue_notification
            queue_notification(kind, pk)
        except Exception:
            logger.warning('Email queue insertion deferred to reconciliation; kind=%s', kind)
    transaction.on_commit(queue, robust=True)


@receiver(post_save, sender=FormSubmission)
def registration_saved(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        after_commit('registration', instance.pk)


@receiver(post_save, sender=SubmissionStatusChange)
def status_saved(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        after_commit('status', instance.pk)


@receiver(post_save, sender=PaymentChange)
def payment_saved(sender, instance, created, raw=False, **kwargs):
    if created and not raw and instance.status == 'verified':
        after_commit('payment', instance.pk)
