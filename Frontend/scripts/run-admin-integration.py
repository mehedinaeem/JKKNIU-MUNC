"""Browser integration with an isolated temporary Django DB; never uses the user's DB."""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.request

frontend = Path(__file__).resolve().parents[1]
backend = frontend.parent / 'Backend'
python = backend / '.venv/bin/python'
if not python.is_file():
    raise SystemExit('Create Backend/.venv and install Backend/requirements.txt first.')
with tempfile.TemporaryDirectory(prefix='munc-admin-e2e-') as directory:
    temporary = Path(directory)
    (temporary / 'e2e_settings.py').write_text('''from config.settings import *
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.environ['MUNC_TEST_DB']}}
CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:4173']
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
LOCAL_PRIVATE_UPLOAD_ROOT = str(__import__('pathlib').Path(os.environ['MUNC_TEST_DB']).parent / 'uploads')
SUBMISSION_RATE_PER_MINUTE = 1000
SUBMISSION_RATE_PER_HOUR = 1000
SUBMISSION_EMAIL_RATE_PER_HOUR = 1000
EMAIL_ENABLED = False
PUBLIC_SITE_URL = 'http://127.0.0.1:4173'
LOGIN_RATE_PER_MINUTE = 100
LOGIN_USERNAME_RATE_PER_15_MINUTES = 100
''')
    env = os.environ.copy()
    env.update(DEBUG='True', SECRET_KEY=secrets.token_urlsafe(64), DATABASE_URL='', USE_SQLITE='True',
               PYTHON_DOTENV_DISABLED='1', DJANGO_SETTINGS_MODULE='e2e_settings', PYTHONPATH=directory,
               MUNC_TEST_DB=str(temporary / 'test.sqlite3'), AUTH_COOKIE_MODE='proxy',
               CORS_ALLOW_CREDENTIALS='True', REDIS_URL='', SUBMISSION_STORAGE_PROVIDER='temporary',
               MUNC_E2E_REVIEWER='isolated-test-reviewer', MUNC_E2E_USERNAME='isolated-test-administrator', MUNC_E2E_PASSWORD=secrets.token_urlsafe(24))
    seed = '''import os, django
django.setup()
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from events.models import Event
call_command('migrate', verbosity=0, interactive=False)
get_user_model().objects.create_superuser(os.environ['MUNC_E2E_USERNAME'], 'test@example.invalid', os.environ['MUNC_E2E_PASSWORD'])
event = Event.objects.create(title='Isolated test conference', slug='isolated-test-conference', event_type='conference', status='published', start_date=timezone.now()+timedelta(days=30))
call_command('seed_registration_templates', event=event.pk, template='all', verbosity=0)
from forms.models import RegistrationForm
from forms.services import publish_form
for form in RegistrationForm.objects.all():
    publish_form(form.pk)
from PIL import Image
Image.new('RGB', (24, 24), 'navy').save(os.path.join(os.path.dirname(os.environ['MUNC_TEST_DB']), 'photo.png'))
from accounts.roles import setup_roles
from accounts.models import EventAssignment
from django.contrib.auth.models import Group
from forms.models import FormField
from registrations.models import FormSubmission, SubmissionFile
from registrations.storage import get_provider
from django.core.files.uploadedfile import SimpleUploadedFile
import uuid
setup_roles()
reviewer = get_user_model().objects.create_user(os.environ['MUNC_E2E_REVIEWER'], password=os.environ['MUNC_E2E_PASSWORD'], is_staff=True)
reviewer.groups.add(Group.objects.get(name='Reviewer'))
EventAssignment.objects.create(user=reviewer, event=event)
review_form = RegistrationForm.objects.create(event=event, title='Review fixture', slug='review-fixture', form_type='test')
FormField.objects.create(form=review_form, key='name', label='Full name', field_type='short_text')
FormField.objects.create(form=review_form, key='committee', label='Committee', field_type='dropdown', options=[{'value': 'ga', 'label': 'General Assembly'}])
FormField.objects.create(form=review_form, key='photo', label='Photo', field_type='file', allowed_extensions=['png'], max_file_size=1048576)
version = publish_form(review_form.pk)
submission = FormSubmission.objects.create(event=event, registration_form=review_form, form_version=version, applicant_email='review-fixture@example.invalid', answers={'name': 'Review fixture applicant', 'committee': 'ga'})
provider = get_provider()
photo = open(os.path.join(os.path.dirname(os.environ['MUNC_TEST_DB']), 'photo.png'), 'rb').read()
provider.upload('applications/1234567890abcdef1234567890abcdef.png', SimpleUploadedFile('photo.png', photo, content_type='image/png'))
SubmissionFile.objects.create(submission=submission, field_key='photo', storage_provider=provider.name, provider_file_id='applications/1234567890abcdef1234567890abcdef.png', original_filename='photo.png', content_type='image/png', file_size=len(photo))
review_form.status = 'closed'
review_form.save()
hidden_event = Event.objects.create(title='Unassigned event', slug='unassigned', event_type='conference', start_date=timezone.now()+timedelta(days=60))
hidden_form = RegistrationForm.objects.create(event=hidden_event, title='Unassigned form', slug='unassigned-form', form_type='test')
FormField.objects.create(form=hidden_form, key='name', label='Name', field_type='short_text')
hidden_version = publish_form(hidden_form.pk)
FormSubmission.objects.create(id=uuid.UUID('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'), event=hidden_event, registration_form=hidden_form, form_version=hidden_version, applicant_email='hidden@example.invalid', answers={'name': 'Hidden applicant'})
'''
    subprocess.run([str(python), '-c', seed], cwd=backend, env=env, check=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    env['MUNC_E2E_PHOTO'] = str(temporary / 'photo.png')
    env['MUNC_E2E_REAL_API'] = f'http://127.0.0.1:{port}/api'
    with tempfile.TemporaryFile(mode='w+') as log:
        server = subprocess.Popen([str(python), 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'], cwd=backend, env=env, stdout=log, stderr=log)
        try:
            for _ in range(40):
                if server.poll() is not None:
                    log.seek(0)
                    raise SystemExit(log.read()[-3000:])
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health/', timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise SystemExit('Temporary Django server did not become ready.')
            result = subprocess.run(['npx', 'playwright', 'test'], cwd=frontend, env=env)
            raise SystemExit(result.returncode)
        finally:
            server.terminate()
            server.wait(timeout=5)
