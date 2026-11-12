"""Private provider adapters. Provider URLs and credentials never enter API payloads."""
import os
from pathlib import Path
import re
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import cloudinary.uploader
import cloudinary.utils
import requests


class StorageError(Exception):
    pass


def check_id(file_id):
    if not re.fullmatch(r'applications/[a-f0-9]{32}\.(pdf|png|jpg|jpeg)', file_id):
        raise StorageError('Invalid private file identifier')
    return file_id


class TemporaryPrivateStorage:
    name = 'temporary'

    def __init__(self):
        if not settings.DEBUG:
            raise ImproperlyConfigured('Temporary file storage is development-only.')
        self.root = Path(settings.LOCAL_PRIVATE_UPLOAD_ROOT)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    def path(self, file_id):
        return self.root / check_id(file_id)

    def upload(self, file_id, upload):
        path = self.path(file_id)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as target:
            for chunk in upload.chunks():
                target.write(chunk)

    def delete(self, file_id):
        self.path(file_id).unlink(missing_ok=True)

    def open(self, file_id):
        return self.path(file_id).open('rb')


class CloudinaryPrivateStorage:
    name = 'cloudinary'

    def options(self):
        options = settings.CLOUDINARY_CONFIG
        if not all(options.get(key) for key in ('cloud_name', 'api_key', 'api_secret')):
            raise ImproperlyConfigured('Private Cloudinary storage is not configured.')
        return {**options, 'secure': True}

    def upload(self, file_id, upload):
        check_id(file_id)
        upload.seek(0)
        result = cloudinary.uploader.upload(upload, public_id=file_id, resource_type='raw',
            type='authenticated', overwrite=False, use_filename=False, unique_filename=False,
            timeout=20, **self.options())
        if result.get('public_id') != file_id or result.get('type') != 'authenticated' or result.get('resource_type') != 'raw':
            raise StorageError('Unexpected private upload response')

    def delete(self, file_id):
        result = cloudinary.uploader.destroy(check_id(file_id), resource_type='raw',
            type='authenticated', invalidate=True, timeout=20, **self.options())
        if result.get('result') not in {'ok', 'not found'}:
            raise StorageError('Private asset cleanup failed')

    def open(self, file_id):
        # Fetch server-side rather than redirecting or returning a signed provider URL.
        url = cloudinary.utils.private_download_url(check_id(file_id), '', resource_type='raw',
            type='authenticated', expires_at=int(time.time()) + 60, attachment=True, **self.options())
        response = requests.get(url, stream=True, timeout=(5, 20), allow_redirects=False)
        if response.status_code != 200:
            response.close()
            raise StorageError('Private download failed')
        return response


def get_provider(name=None):
    name = name or settings.SUBMISSION_STORAGE_PROVIDER
    if name == 'cloudinary':
        provider = CloudinaryPrivateStorage()
        provider.options()  # Fail before upload intent persistence if credentials are absent.
        return provider
    if name == 'temporary':
        return TemporaryPrivateStorage()
    raise ImproperlyConfigured('Unsupported submission storage provider.')
