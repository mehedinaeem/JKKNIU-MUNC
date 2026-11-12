from django.conf import settings
from django.core.checks import Error, register, Tags


@register(Tags.security, deploy=True)
def submission_configuration(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    errors = []
    if settings.SUBMISSION_STORAGE_PROVIDER != 'cloudinary' or not all(settings.CLOUDINARY_CONFIG.values()):
        errors.append(Error('Configure persistent authenticated Cloudinary storage before production submissions.', id='registrations.E001'))
    if not settings.REDIS_URL:
        errors.append(Error('Configure REDIS_URL for shared production submission rate limits.', id='registrations.E002'))
    return errors
