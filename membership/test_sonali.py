import json
from unittest.mock import patch
import requests
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from .verification import StudentVerificationService, VerificationUnavailable
from .sonali import SonaliBankStudentProvider, PAGE_URL, LOOKUP_URL
from .models import StudentIdentity


@override_settings(DEBUG=True, MEMBERSHIP_VERIFICATION_PROVIDER='sonali_bank')
class SonaliLookupTests(TestCase):
    def setUp(self):
        self.session_patch = patch('membership.sonali.requests.Session')
        self.session = self.session_patch.start().return_value.__enter__.return_value
        self.addCleanup(self.session_patch.stop)
        self.page = self.session.get.return_value.__enter__.return_value
        self.page.status_code = 200
        self.response = self.session.post.return_value.__enter__.return_value
        self.response.status_code = 200
        self.response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.payload({'StudentId': 12345, 'Name': 'Test Student', 'DeptName': 'English', 'ErrorMessage': ''})
    def payload(self, data):
        self.response.iter_content.return_value = [json.dumps(data).encode()]
    def test_observed_contract_and_only_entered_record(self):
        identity = StudentVerificationService().verify('test-123')
        self.assertEqual(identity.registration_number, 'TEST-123')
        self.assertEqual(identity.student_id, '12345')
        self.assertEqual(identity.full_name, 'Test Student')
        self.assertEqual(identity.department, 'English')
        self.assertEqual(identity.session, '')
        self.assertEqual(identity.verification_source, 'sonali_jkkniu_fee_lookup')
        self.session.get.assert_called_once_with(PAGE_URL, timeout=(3, 8), allow_redirects=False, stream=True)
        self.session.post.assert_called_once()
        args = self.session.post.call_args
        self.assertEqual(args.args, (LOOKUP_URL,))
        self.assertEqual(args.kwargs['data'], {'id': 'TEST-123'})
        self.assertFalse(args.kwargs['allow_redirects'])
    def test_provider_errors_do_not_disclose_response(self):
        self.payload({'ErrorMessage': 'PRIVATE provider data'})
        with self.assertRaises(ValidationError) as error:
            StudentVerificationService().verify('TEST-123')
        self.assertNotIn('PRIVATE', str(error.exception))
        self.assertFalse(StudentIdentity.objects.exists())
    def test_unknown_shapes_missing_fields_and_html_challenges_fail_closed(self):
        for data in [[], {}, {'Name': 'Student'}, {'Name': 'Student', 'DeptName': 'English', 'StudentId': True}]:
            self.payload(data)
            with self.assertRaises(VerificationUnavailable): SonaliBankStudentProvider().verify('TEST-123')
        self.response.headers = {'Content-Type': 'text/html'}
        with self.assertRaises(VerificationUnavailable): SonaliBankStudentProvider().verify('TEST-123')
    def test_redirect_timeout_rate_limit_and_size_limits(self):
        self.page.status_code = 302
        with self.assertRaises(VerificationUnavailable): SonaliBankStudentProvider().verify('TEST-123')
        self.page.status_code = 200
        self.session.post.side_effect = requests.Timeout('private network details')
        with self.assertRaises(VerificationUnavailable): SonaliBankStudentProvider().verify('TEST-123')
        self.session.post.side_effect = None
        self.response.status_code = 429
        with self.assertRaises(VerificationUnavailable): SonaliBankStudentProvider().verify('TEST-123')
        self.response.status_code = 200
        self.response.iter_content.return_value = [b'x' * 65537]
        with self.assertRaises(VerificationUnavailable): SonaliBankStudentProvider().verify('TEST-123')
    def test_public_application_does_not_return_student_record(self):
        from django.core.cache import cache
        cache.clear()
        client = APIClient()
        checked = client.post('/api/membership/lookup/', {'registration_number': 'TEST-123', 'consent': True}, format='json')
        self.assertEqual(checked.status_code, 200)
        self.assertNotEqual(checked.data['student']['student_id'], '12345')
        response = client.post('/api/membership/apply/', {'registration_number': 'TEST-123', 'lookup_token': checked.data['lookup_token'], 'identity_confirmed': True, 'is_existing_member': False, 'contact_email': 'applicant@example.invalid', 'motivation': 'I would like to contribute to diplomacy.', 'consent': True}, format='json')
        self.assertEqual(response.status_code, 202)
        self.assertNotIn('Test Student', str(response.data))
        self.assertNotIn('12345', str(response.data))
    def test_mobile_and_email_from_provider_are_not_trusted(self):
        self.payload({'StudentId': 'S-123', 'Name': 'Test Student', 'DeptName': 'English', 'MobileNo': 'untrusted', 'Email': 'untrusted@example.invalid'})
        record = SonaliBankStudentProvider().verify('TEST-123')
        self.assertFalse(hasattr(record, 'phone'))
        self.assertFalse(hasattr(record, 'email'))
