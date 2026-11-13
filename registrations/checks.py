from django.conf import settings
from django.core.checks import Error, register, Tags


@register(Tags.security, deploy=True)
def submission_configuration(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    errors = []
    if settings.SUBMISSION_STORAGE_PROVIDER != 'cloudinary' or not all(settings.CLOUDINARY_CONFIG.values()):
        errors.append(Error('Configure persistent authenticated Cloudinary storage before production submissions.', id='registrations.E001'))
    from accounts.rate_limits import selected_backend
    if selected_backend() == 'redis' and not settings.REDIS_URL:
        errors.append(Error('Redis rate limiting requires REDIS_URL.', id='registrations.E002'))
    if selected_backend() == 'database' and settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        errors.append(Error('Production database rate limiting requires PostgreSQL.', id='registrations.E003'))
    return errors
