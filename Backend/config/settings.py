"""Environment-driven settings for the independent Django API."""
import os
import json
import tempfile
from urllib.parse import urlsplit, unquote
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(name, default=False):
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ImproperlyConfigured(f"{name} must be a boolean")
    return value in {"true", "1", "yes"}


def env_list(name, default=""):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


DEBUG = env_bool("DEBUG")
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY == "replace-with-your-local-development-key":
    raise ImproperlyConfigured("Set SECRET_KEY to your own key in the environment or .env")
if not DEBUG and (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-")):
    raise ImproperlyConfigured("Production requires a strong SECRET_KEY of at least 50 characters")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]" if DEBUG else "")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must contain explicit hostnames")

INSTALLED_APPS = [
    "accounts.apps.RoleAdminConfig", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "accounts.apps.AccountsConfig",
    "events.apps.EventsConfig", "forms.apps.FormsConfig",
    "registrations.apps.RegistrationsConfig",
    "mailing.apps.MailingConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "accounts.middleware.AdminNoStoreMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(
        DATABASE_URL, conn_max_age=60, conn_health_checks=True,
        ssl_require=env_bool("DATABASE_SSL_REQUIRE", not DEBUG),
    )}
    if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise ImproperlyConfigured("DATABASE_URL must point to PostgreSQL")
elif DEBUG and env_bool("USE_SQLITE", True):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    raise ImproperlyConfigured("Set DATABASE_URL; SQLite fallback is only available with DEBUG=True and USE_SQLITE=True")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in ["UserAttributeSimilarityValidator", "MinimumLengthValidator",
                 "CommonPasswordValidator", "NumericPasswordValidator"]
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Configure a durable private storage backend before accepting production file answers.
# Options are trusted deployment configuration, never supplied by form authors.
try:
    private_storage_options = json.loads(os.getenv('PRIVATE_UPLOAD_STORAGE_OPTIONS', '{}'))
except ValueError as exc:
    raise ImproperlyConfigured('PRIVATE_UPLOAD_STORAGE_OPTIONS must be a JSON object') from exc
if not isinstance(private_storage_options, dict):
    raise ImproperlyConfigured('PRIVATE_UPLOAD_STORAGE_OPTIONS must be a JSON object')
STORAGES['private_uploads'] = {
    'BACKEND': os.getenv('PRIVATE_UPLOAD_STORAGE_BACKEND', 'registrations.models.PrivateUploadStorage'),
    'OPTIONS': private_storage_options,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173" if DEBUG else "")
CORS_URLS_REGEX = r"^/api/.*$"
CORS_EXPOSE_HEADERS = ["Content-Disposition"]
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173" if DEBUG else "")
# Heroku's router sets X-Forwarded-Proto. Trust only a controlled proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
# Subdomains and preload require a separate domain-wide rollout decision.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}, "null": {"class": "logging.NullHandler"}},
    "loggers": {name: {"handlers": ["null"], "propagate": False} for name in ("pypdf", "cloudinary")},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Anonymous submission admission and private storage.
REDIS_URL = os.getenv('REDIS_URL', '').strip()
CACHES = {'default': (
    {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}
    if REDIS_URL else {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'submission-limits'}
)}
REST_FRAMEWORK['NUM_PROXIES'] = int(os.getenv('TRUSTED_PROXY_COUNT', '0' if DEBUG else '1'))
SUBMISSION_RATE_PER_MINUTE = int(os.getenv('SUBMISSION_RATE_PER_MINUTE', '5'))
SUBMISSION_RATE_PER_HOUR = int(os.getenv('SUBMISSION_RATE_PER_HOUR', '30'))
SUBMISSION_EMAIL_RATE_PER_HOUR = int(os.getenv('SUBMISSION_EMAIL_RATE_PER_HOUR', '5'))
SUBMISSION_STORAGE_PROVIDER = os.getenv('SUBMISSION_STORAGE_PROVIDER', 'temporary' if DEBUG else 'cloudinary')
if SUBMISSION_STORAGE_PROVIDER not in {'temporary', 'cloudinary'} or (not DEBUG and SUBMISSION_STORAGE_PROVIDER != 'cloudinary'):
    raise ImproperlyConfigured('Production submissions require persistent private Cloudinary storage.')
LOCAL_PRIVATE_UPLOAD_ROOT = os.getenv('LOCAL_PRIVATE_UPLOAD_ROOT', str(Path(tempfile.gettempdir()) / f'jkkniu-private-{os.getuid()}'))
CLOUDINARY_CONFIG = {
    'cloud_name': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    'api_key': os.getenv('CLOUDINARY_API_KEY', ''),
    'api_secret': os.getenv('CLOUDINARY_API_SECRET', ''),
}
if os.getenv('CLOUDINARY_URL'):
    cloudinary_url = urlsplit(os.environ['CLOUDINARY_URL'])
    if cloudinary_url.scheme != 'cloudinary':
        raise ImproperlyConfigured('CLOUDINARY_URL must use the cloudinary scheme.')
    CLOUDINARY_CONFIG = {'cloud_name': cloudinary_url.hostname, 'api_key': unquote(cloudinary_url.username or ''),
                         'api_secret': unquote(cloudinary_url.password or '')}
DATA_UPLOAD_MAX_NUMBER_FILES = 10
DATA_UPLOAD_MAX_NUMBER_FIELDS = 120
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

FILE_UPLOAD_HANDLERS = [
    'registrations.parsers.UploadByteLimit',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
if min(SUBMISSION_RATE_PER_MINUTE, SUBMISSION_RATE_PER_HOUR, SUBMISSION_EMAIL_RATE_PER_HOUR) < 1:
    raise ImproperlyConfigured('Submission rate limits must be positive integers.')
if REST_FRAMEWORK['NUM_PROXIES'] < 0:
    raise ImproperlyConfigured('TRUSTED_PROXY_COUNT cannot be negative.')


# Session authentication: proxy first; cross-site cookies require an explicit secure opt-in.
AUTH_COOKIE_MODE = os.getenv('AUTH_COOKIE_MODE', 'proxy')
if AUTH_COOKIE_MODE not in {'proxy', 'cross_site'}:
    raise ImproperlyConfigured('AUTH_COOKIE_MODE must be proxy or cross_site.')
SESSION_COOKIE_NAME = 'jkkniu_admin_session'
CSRF_COOKIE_NAME = 'jkkniu_csrf'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_SAMESITE = 'None' if AUTH_COOKIE_MODE == 'cross_site' else 'Lax'
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
SESSION_COOKIE_AGE = int(os.getenv('ADMIN_SESSION_MAX_AGE', '28800'))
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
CSRF_FAILURE_VIEW = 'accounts.views.csrf_failure'
CORS_ALLOW_CREDENTIALS = env_bool('CORS_ALLOW_CREDENTIALS', DEBUG or AUTH_COOKIE_MODE == 'cross_site')
if AUTH_COOKIE_MODE == 'cross_site':
    if DEBUG or not CORS_ALLOW_CREDENTIALS or not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured('Cross-site sessions require production HTTPS and explicit credentialed CORS origins.')
    if (any(not origin.startswith('https://') or '*' in origin or origin not in CSRF_TRUSTED_ORIGINS for origin in CORS_ALLOWED_ORIGINS)
            or any(not origin.startswith('https://') or '*' in origin for origin in CSRF_TRUSTED_ORIGINS)):
        raise ImproperlyConfigured('Cross-site CORS origins must be exact HTTPS CSRF-trusted origins.')
LOGIN_RATE_PER_MINUTE = int(os.getenv('LOGIN_RATE_PER_MINUTE', '10'))
LOGIN_RATE_PER_HOUR = int(os.getenv('LOGIN_RATE_PER_HOUR', '100'))
LOGIN_USERNAME_RATE_PER_15_MINUTES = int(os.getenv('LOGIN_USERNAME_RATE_PER_15_MINUTES', '10'))
if min(LOGIN_RATE_PER_MINUTE, LOGIN_RATE_PER_HOUR, LOGIN_USERNAME_RATE_PER_15_MINUTES, SESSION_COOKIE_AGE) < 1:
    raise ImproperlyConfigured('Login limits and session age must be positive integers.')

# Durable email queue. Enabling transport requires explicit operator configuration.
EMAIL_ENABLED = env_bool('EMAIL_ENABLED', False)
EMAIL_PROVIDER = os.getenv('EMAIL_PROVIDER', 'brevo')
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_WEBHOOK_TOKEN = os.getenv('BREVO_WEBHOOK_TOKEN', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', '')
DEFAULT_FROM_NAME = os.getenv('DEFAULT_FROM_NAME', 'JKKNIU Model United Nations Club')
PUBLIC_SITE_URL = os.getenv('PUBLIC_SITE_URL', 'http://localhost:5173' if DEBUG else '').rstrip('/')
PUBLIC_API_URL = os.getenv('PUBLIC_API_URL', 'http://localhost:8000/api' if DEBUG else (f'{PUBLIC_SITE_URL}/api' if PUBLIC_SITE_URL else '')).rstrip('/')
EMAIL_DAILY_LIMIT = int(os.getenv('EMAIL_DAILY_LIMIT', '300'))
EMAIL_TRANSACTIONAL_RESERVE = int(os.getenv('EMAIL_TRANSACTIONAL_RESERVE', '50'))
EMAIL_RATE_PER_MINUTE = int(os.getenv('EMAIL_RATE_PER_MINUTE', '60'))
EMAIL_CONNECT_TIMEOUT = float(os.getenv('EMAIL_CONNECT_TIMEOUT', '5'))
EMAIL_READ_TIMEOUT = float(os.getenv('EMAIL_READ_TIMEOUT', '20'))
EMAIL_MAX_ATTEMPTS = int(os.getenv('EMAIL_MAX_ATTEMPTS', '5'))
EMAIL_RETRY_BASE_SECONDS = int(os.getenv('EMAIL_RETRY_BASE_SECONDS', '60'))
EMAIL_LEASE_SECONDS = int(os.getenv('EMAIL_LEASE_SECONDS', '180'))
EMAIL_RETENTION_DAYS = int(os.getenv('EMAIL_RETENTION_DAYS', '180'))
EMAIL_QUOTA_TIME_ZONE = os.getenv('EMAIL_QUOTA_TIME_ZONE', 'UTC')
EMAIL_CAMPAIGN_MAX_RECIPIENTS = int(os.getenv('EMAIL_CAMPAIGN_MAX_RECIPIENTS', '10000'))
if EMAIL_PROVIDER != 'brevo' or not 0 <= EMAIL_TRANSACTIONAL_RESERVE <= EMAIL_DAILY_LIMIT or min(EMAIL_DAILY_LIMIT, EMAIL_RATE_PER_MINUTE, EMAIL_MAX_ATTEMPTS, EMAIL_RETRY_BASE_SECONDS, EMAIL_RETENTION_DAYS, EMAIL_CAMPAIGN_MAX_RECIPIENTS, EMAIL_CONNECT_TIMEOUT, EMAIL_READ_TIMEOUT) <= 0:
    raise ImproperlyConfigured('Invalid email queue/provider settings.')
if EMAIL_LEASE_SECONDS <= EMAIL_CONNECT_TIMEOUT + EMAIL_READ_TIMEOUT + 30:
    raise ImproperlyConfigured('EMAIL_LEASE_SECONDS must exceed provider timeouts plus 30 seconds.')

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import urlsplit
try:
    ZoneInfo(EMAIL_QUOTA_TIME_ZONE)
except ZoneInfoNotFoundError:
    raise ImproperlyConfigured('Use an IANA timezone for EMAIL_QUOTA_TIME_ZONE.') from None
for mail_url in (PUBLIC_SITE_URL, PUBLIC_API_URL):
    if mail_url:
        parsed_mail_url = urlsplit(mail_url)
        if parsed_mail_url.scheme not in ({'http', 'https'} if DEBUG else {'https'}) or not parsed_mail_url.netloc or parsed_mail_url.username or parsed_mail_url.password or parsed_mail_url.query or parsed_mail_url.fragment:
            raise ImproperlyConfigured('Public email URLs must be absolute trusted HTTPS URLs in production, without credentials/query/fragment.')
