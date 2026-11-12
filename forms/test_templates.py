from io import StringIO
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone
from events.models import Event
from forms.models import RegistrationForm
from forms.services import publish_form


class RegistrationTemplateTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(title='Template test', slug='template-test', event_type='conference', start_date=timezone.now())

    def test_editable_drafts_include_both_complete_templates(self):
        call_command('seed_registration_templates', event=self.event.pk, stdout=StringIO())
        forms = self.event.registration_forms.all()
        self.assertEqual(forms.count(), 2)
        delegate = forms.get(form_type='delegate')
        board = forms.get(form_type='executive-board')
        self.assertEqual(delegate.fields.count(), 14)
        self.assertEqual(board.fields.count(), 12)
        self.assertEqual(delegate.status, 'draft')
        self.assertEqual(delegate.versions.count(), 0)
        self.assertTrue(delegate.fields.filter(key='passport_photo', field_type='file').exists())
        self.assertTrue(delegate.fields.filter(key='payment_screenshot', field_type='file').exists())
        self.assertEqual(board.fields.get(key='cv').allowed_extensions, ['pdf'])
        self.assertTrue(board.fields.get(key='data_processing_consent').required)
        publish_form(delegate.pk)
        publish_form(board.pk)
        self.assertEqual(delegate.versions.count(), 1)

    def test_reseeding_never_overwrites_admin_edits(self):
        call_command('seed_registration_templates', event=self.event.pk, template='delegate', stdout=StringIO())
        form = RegistrationForm.objects.get(event=self.event)
        form.title = 'Edited by organiser'
        form.save()
        field = form.fields.get(key='full_name')
        field.label = 'Preferred full name'
        field.save()
        call_command('seed_registration_templates', event=self.event.pk, template='delegate', stdout=StringIO())
        form.refresh_from_db(); field.refresh_from_db()
        self.assertEqual(form.title, 'Edited by organiser')
        self.assertEqual(field.label, 'Preferred full name')
        self.assertEqual(RegistrationForm.objects.count(), 1)

    def test_requires_an_existing_explicit_event(self):
        with self.assertRaises(CommandError):
            call_command('seed_registration_templates', event=999999, stdout=StringIO())
        self.assertFalse(RegistrationForm.objects.exists())
