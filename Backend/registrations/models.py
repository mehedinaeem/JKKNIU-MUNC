import uuid
from django.conf import settings
from django.db import models
from django.core.files.storage import FileSystemStorage, storages
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateUploadStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.BASE_DIR / "private_uploads", base_url=None)

    def url(self, name):
        raise NotImplementedError("Private uploads require authenticated download.")


def private_upload_storage():
    return storages["private_uploads"]


def upload_path(instance, filename):
    from pathlib import Path
    return f"answers/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey("club_forms.FormVersion", on_delete=models.PROTECT, related_name="submissions")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    answers = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class SubmissionFile(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="files")
    field_key = models.SlugField(max_length=100)
    file = models.FileField(storage=private_upload_storage, upload_to=upload_path)
