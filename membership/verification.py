"""Only university-authorized adapters may supply identity records. No bank URLs are invented."""
import re
from dataclasses import dataclass
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.exceptions import APIException, ValidationError
from .models import StudentIdentity
from django.utils import timezone


class VerificationUnavailable(APIException):
    status_code = 503
    default_detail = 'Student verification is unavailable. Please contact the club office.'


@dataclass(frozen=True)
class StudentRecord:
    registration_number: str
    full_name: str
    department: str
    source: str
    student_id: str = ''
    session: str = ''


class StudentVerificationProvider:
    def verify(self, registration_number):
        raise NotImplementedError


class MockStudentProvider(StudentVerificationProvider):
    """Explicit fixtures only; never guesses students or accepts arbitrary numbers."""
    def verify(self, registration_number):
        if not settings.DEBUG or not settings.MEMBERSHIP_ALLOW_MOCK:
            raise VerificationUnavailable()
        row = settings.MEMBERSHIP_MOCK_STUDENTS.get(registration_number)
        if not row:
            raise ValidationError({'detail': 'Unable to verify the supplied application. Contact the club office.'})
        return StudentRecord(registration_number=registration_number, source='development_mock', **row)


class StudentVerificationService:
    def verify(self, registration_number):
        registration_number = registration_number.strip()
        if settings.MEMBERSHIP_VERIFICATION_PROVIDER == 'sonali_bank':
            registration_number = registration_number.upper()
        if not re.fullmatch(r'[A-Za-z0-9/-]{3,64}', registration_number):
            raise ValidationError({'registration_number': 'Enter a valid registration number.'})
        provider = settings.MEMBERSHIP_VERIFICATION_PROVIDER
        if provider == 'mock':
            adapter = MockStudentProvider()
        elif provider == 'sonali_bank':
            from .sonali import SonaliBankStudentProvider
            adapter = SonaliBankStudentProvider()
        elif provider and provider != 'disabled':
            try: adapter = import_string(provider)()
            except Exception: raise VerificationUnavailable() from None
        else:
            raise VerificationUnavailable()
        try:
            record = adapter.verify(registration_number)
            if not isinstance(record, StudentRecord) or record.registration_number != registration_number or not record.full_name or not record.department or not record.source:
                raise VerificationUnavailable()
            for value, maximum in [(record.full_name, 255), (record.department, 255), (record.student_id, 64), (record.session, 100), (record.source, 100)]:
                if not isinstance(value, str) or len(value) > maximum: raise VerificationUnavailable()
        except (ValidationError, VerificationUnavailable):
            raise
        except Exception:
            raise VerificationUnavailable() from None
        identity, _ = StudentIdentity.objects.update_or_create(registration_number=record.registration_number,
            defaults={'student_id': record.student_id or None, 'full_name': record.full_name,
                'department': record.department, 'session': record.session, 'verification_source': record.source,
                'last_checked_at': timezone.now()})
        return identity
