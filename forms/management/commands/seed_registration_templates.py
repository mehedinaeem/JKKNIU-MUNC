from copy import deepcopy
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from events.models import Event
from forms.models import RegistrationForm, FormField
from forms.serializers import FormFieldSerializer
from forms.templates import TEMPLATES


class Command(BaseCommand):
    help = 'Create editable draft Delegate/Executive Board forms for an explicitly selected event. Existing records are never overwritten.'

    def add_arguments(self, parser):
        parser.add_argument('--event', type=int, required=True)
        parser.add_argument('--template', choices=['all', *TEMPLATES], default='all')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            event = Event.objects.get(pk=options['event'])
        except Event.DoesNotExist:
            raise CommandError('Choose an existing event ID.') from None
        names = TEMPLATES if options['template'] == 'all' else [options['template']]
        for name in names:
            data = deepcopy(TEMPLATES[name])
            form, created = RegistrationForm.objects.get_or_create(slug=f'event-{event.pk}-{name}', defaults={
                'event': event, 'title': data['title'], 'description': data['description'], 'form_type': name})
            if form.event_id != event.pk:
                raise CommandError('The template slug is already used by another event.')
            if not created:
                self.stdout.write(f'Skipped existing form: {form.slug}')
                continue
            for index, field in enumerate(data['fields']):
                validator = FormFieldSerializer(data={**field, 'display_order': index})
                validator.is_valid(raise_exception=True)
                FormField.objects.create(form=form, **validator.validated_data)
            self.stdout.write(self.style.SUCCESS(f'Created draft: {form.title} ({form.slug})'))
        self.stdout.write('Review choices, dates, capacity, payment instructions and consent text in the Form Builder before publishing.')
