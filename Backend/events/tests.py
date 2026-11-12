from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event
from forms.models import RegistrationForm
from forms.serializers import RegistrationFormSerializer


class EventAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = get_user_model().objects.create_user(username='staff', is_staff=True)
        self.member = get_user_model().objects.create_user(username='member')
        self.start = timezone.now() + timedelta(days=30)
        self.event = Event.objects.create(title='Public conference', slug='public-conference',
            event_type='conference', start_date=self.start, end_date=self.start + timedelta(days=1),
            status='published')
        self.draft = Event.objects.create(title='Private draft', slug='private-draft',
            event_type='workshop', start_date=self.start, status='draft')

    def payload(self, **changes):
        data = {'title': 'New event', 'slug': 'new-event', 'event_type': 'custom-type',
                'start_date': self.start.isoformat()}
        data.update(changes)
        return data

    def test_public_list_and_detail_only_show_published(self):
        for status in ('completed', 'cancelled'):
            Event.objects.create(title=status, slug=status, event_type='other', start_date=self.start, status=status)
        for user in (None, self.staff):
            self.client.force_authenticate(user)
            response = self.client.get('/api/events/?status=draft')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['count'], 1)
            self.assertEqual(response.data['results'][0]['slug'], self.event.slug)
            self.assertEqual(self.client.get('/api/events/public-conference/').status_code, 200)
            for slug in ('private-draft', 'completed', 'cancelled', 'missing'):
                self.assertEqual(self.client.get(f'/api/events/{slug}/').status_code, 404)

    def test_anonymous_member_and_inactive_staff_cannot_write(self):
        inactive = get_user_model().objects.create_user(username='inactive', is_staff=True, is_active=False)
        for user in (None, self.member, inactive):
            self.client.force_authenticate(user)
            with self.subTest(user=user):
                self.assertEqual(self.client.post('/api/admin/events/', self.payload(), format='json').status_code, 403)
                self.assertEqual(self.client.patch(f'/api/admin/events/{self.draft.pk}/', {'title': 'Denied'}, format='json').status_code, 403)
                self.assertEqual(self.client.delete(f'/api/admin/events/{self.draft.pk}/').status_code, 403)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.title, 'Private draft')

    def test_staff_create_patch_publish_delete(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post('/api/admin/events/', self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['status'], 'draft')
        self.assertEqual(response.data['organizer'], self.staff.pk)
        pk = response.data['id']
        self.assertEqual(self.client.get('/api/events/new-event/').status_code, 404)
        response = self.client.patch(f'/api/admin/events/{pk}/', {'status': 'published'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get('/api/events/new-event/').status_code, 200)
        self.assertEqual(self.client.delete(f'/api/admin/events/{pk}/').status_code, 204)
        self.assertFalse(Event.objects.filter(pk=pk).exists())

    def test_unique_slug_invalid_choices_dates_urls_and_organizer(self):
        self.client.force_authenticate(self.staff)
        for changes in ({'slug': self.event.slug}, {'status': 'unknown'},
                        {'end_date': (self.start - timedelta(days=1)).isoformat()},
                        {'registration_start': self.start.isoformat(), 'registration_end': (self.start - timedelta(days=1)).isoformat()},
                        {'cover_image': 'javascript:alert(1)'}, {'organizer': 999999}, {'slug': ''}):
            response = self.client.post('/api/admin/events/', self.payload(**changes), format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_patch_validates_existing_other_half_of_date_window(self):
        self.client.force_authenticate(self.staff)
        response = self.client.patch(f'/api/admin/events/{self.event.pk}/',
            {'start_date': (self.start + timedelta(days=2)).isoformat()}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('end_date', response.data)
        self.event.refresh_from_db()
        self.assertEqual(self.event.start_date, self.start)

    def test_filter_search_order_and_pagination(self):
        for i in range(26):
            Event.objects.create(title=f'Workshop {i:02d}', slug=f'workshop-{i}',
                description='Diplomacy practice', event_type='workshop',
                start_date=self.start + timedelta(days=2), status='published')
        response = self.client.get('/api/events/')
        self.assertEqual(response.data['count'], 27)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(self.client.get('/api/events/?page=2').data['results']), 2)
        response = self.client.get('/api/events/', {'event_type': 'workshop', 'search': 'diplomacy', 'ordering': 'title'})
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(response.data['results'][0]['title'], 'Workshop 00')
        self.assertEqual(self.client.get('/api/events/', {'search': 'Private draft'}).data['count'], 0)
        self.assertEqual(self.client.get('/api/events/', {'start_date_after': (self.start + timedelta(days=1)).isoformat()}).data['count'], 26)
        self.assertEqual(self.client.get('/api/events/', {'start_date_before': self.start.isoformat()}).data['count'], 1)
        for params in ({'start_date_after': 'invalid'}, {'ordering': 'organizer__password'}):
            self.assertEqual(self.client.get('/api/events/', params).status_code, 400)

    def test_public_write_and_unrequested_admin_methods_not_supported(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post('/api/events/', self.payload(), format='json').status_code, 405)
        self.assertEqual(self.client.put(f'/api/admin/events/{self.event.pk}/', self.payload(), format='json').status_code, 405)
        self.assertEqual(self.client.get(f'/api/admin/events/{self.event.pk}/').status_code, 405)
        self.assertEqual(self.client.patch('/api/admin/events/999999/', {}, format='json').status_code, 404)

    def test_session_authentication_requires_csrf_on_write(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.staff)
        response = client.post('/api/admin/events/', self.payload(), format='json')
        self.assertEqual(response.status_code, 403)


class RegistrationFormTests(TestCase):
    def setUp(self):
        self.start = timezone.now()
        self.event = Event.objects.create(title='Test', slug='test', event_type='custom', start_date=self.start)

    def test_multiple_forms_custom_types_and_cascade(self):
        for i, kind in enumerate(('delegate', 'my-custom-application')):
            serializer = RegistrationFormSerializer(data={'event': self.event.pk, 'title': kind,
                'slug': f'form-{i}', 'form_type': kind})
            self.assertTrue(serializer.is_valid(), serializer.errors)
            serializer.save()
        self.assertEqual(self.event.registration_forms.count(), 2)
        self.event.delete()
        self.assertEqual(RegistrationForm.objects.count(), 0)

    def test_form_validation_and_partial_window(self):
        base = {'event': self.event.pk, 'title': 'Application', 'slug': 'application', 'form_type': 'custom'}
        for extra in ({'capacity': 0}, {'capacity': -1}, {'status': 'invalid'},
                      {'opens_at': self.start.isoformat(), 'closes_at': (self.start - timedelta(days=1)).isoformat()}):
            serializer = RegistrationFormSerializer(data={**base, **extra})
            self.assertFalse(serializer.is_valid())
        serializer = RegistrationFormSerializer(data={**base, 'capacity': None})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        form = serializer.save(opens_at=self.start, closes_at=self.start + timedelta(days=1))
        self.assertFalse(RegistrationFormSerializer(data=base).is_valid())
        serializer = RegistrationFormSerializer(form, data={'opens_at': (self.start + timedelta(days=2)).isoformat()}, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_database_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RegistrationForm.objects.create(event=self.event, title='Bad', slug='bad', form_type='custom', capacity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Event.objects.create(title='Bad', slug='bad', event_type='custom', start_date=self.start, end_date=self.start - timedelta(days=1))

    @override_settings(DEBUG=True)
    def test_demo_command_is_idempotent_and_preserves_edits(self):
        call_command('seed_demo_events', stdout=StringIO())
        demo = Event.objects.get(slug='demo-national-mun-2027')
        demo.title = 'Edited by admin'
        demo.save()
        call_command('seed_demo_events', stdout=StringIO())
        demo.refresh_from_db()
        self.assertEqual(demo.title, 'Edited by admin')
        self.assertEqual(demo.registration_forms.count(), 4)

    @override_settings(DEBUG=False)
    def test_demo_command_rejects_production(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo_events', stdout=StringIO())
