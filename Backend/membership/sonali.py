"""Single-record adapter for the public lookup used by JKKNIU's Sonali fee page.

Contract observed in that page's JavaScript: POST form `id` (upper case),
JSON StudentId / Name / DeptName / ErrorMessage. No guessed identity fields,
payment submission, record enumeration, CAPTCHA workaround or phone trust.
"""
import json
import time
import requests
from rest_framework.exceptions import ValidationError
from .verification import StudentRecord, StudentVerificationProvider, VerificationUnavailable

PAGE_URL = 'https://billpay.sonalibank.com.bd/JKKNIU/SemesterFee/Honours'
LOOKUP_URL = 'https://billpay.sonalibank.com.bd/JKKNIU/SemesterFee/GetStudent'


class SonaliBankStudentProvider(StudentVerificationProvider):
    def verify(self, registration_number):
        deadline = time.monotonic() + 20
        try:
            with requests.Session() as session:
                # Follow the ordinary page flow; never fabricate/bypass security tokens.
                with session.get(PAGE_URL, timeout=(3, 8), allow_redirects=False, stream=True) as page:
                    if page.status_code != 200:
                        raise VerificationUnavailable()
                with session.post(LOOKUP_URL, data={'id': registration_number.upper()},
                    headers={'Accept': 'application/json', 'Referer': PAGE_URL,
                        'Origin': 'https://billpay.sonalibank.com.bd', 'X-Requested-With': 'XMLHttpRequest'},
                    timeout=(3, 8), allow_redirects=False, stream=True) as response:
                    if response.status_code != 200 or 'application/json' not in response.headers.get('Content-Type', '').lower():
                        raise VerificationUnavailable()
                    chunks, size = [], 0
                    for chunk in response.iter_content(8192):
                        if time.monotonic() > deadline: raise VerificationUnavailable()
                        size += len(chunk)
                        if size > 65536: raise VerificationUnavailable()
                        chunks.append(chunk)
                    data = json.loads(b''.join(chunks))
        except VerificationUnavailable:
            raise
        except (requests.RequestException, ValueError, UnicodeError):
            raise VerificationUnavailable() from None
        if not isinstance(data, dict): raise VerificationUnavailable()
        if data.get('ErrorMessage'):
            raise ValidationError({'detail': 'Unable to verify the supplied application. Contact the club office.'})
        name, department, student_id = data.get('Name'), data.get('DeptName'), data.get('StudentId')
        if not isinstance(name, str) or not name.strip() or not isinstance(department, str) or not department.strip():
            raise VerificationUnavailable()
        if not isinstance(student_id, (str, int)) or isinstance(student_id, bool) or not str(student_id).strip():
            raise VerificationUnavailable()
        # No academic session, email or phone is proven by the observed lookup contract.
        return StudentRecord(registration_number=registration_number, full_name=name.strip(),
            department=department.strip(), student_id=str(student_id).strip(), source='sonali_jkkniu_fee_lookup')
