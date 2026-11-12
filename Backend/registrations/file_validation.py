"""Decode supported media; do not infer trust from filenames or browser MIME headers."""
from io import BytesIO
from pathlib import Path
import re
import warnings

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.text import get_valid_filename
from rest_framework.exceptions import ValidationError
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject

ALLOWED = {'pdf': 'application/pdf', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}
DANGEROUS_PDF_KEYS = {'/JS', '/JavaScript', '/Launch', '/EmbeddedFiles', '/RichMedia', '/XFA',
                      '/OpenAction', '/AA', '/A', '/AcroForm'}


def safe_filename(name):
    name = str(name).replace('\\', '/').split('/')[-1]
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    try:
        name = get_valid_filename(name)
    except Exception:
        raise ValidationError('Invalid filename.')
    return name[:150 - len(Path(name).suffix)] + Path(name).suffix.lower() if len(name) > 150 else name


def check_pdf(data):
    if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-1024:]:
        raise ValueError('Invalid PDF signature')
    reader = PdfReader(BytesIO(data), strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 200:
        raise ValueError('Encrypted, empty or excessive PDF')
    visited = set()
    count = 0

    def visit(obj, depth=0):
        nonlocal count
        count += 1
        if depth > 40 or count > 20000:
            raise ValueError('PDF complexity exceeds supported limits')
        if isinstance(obj, IndirectObject):
            key = (obj.idnum, obj.generation)
            if key in visited:
                return
            visited.add(key)
            obj = obj.get_object()
        if isinstance(obj, DictionaryObject):
            if DANGEROUS_PDF_KEYS.intersection(obj.keys()):
                raise ValueError('Active PDF content is unsupported')
            for value in obj.values():
                visit(value, depth + 1)
        elif isinstance(obj, ArrayObject):
            for value in obj:
                visit(value, depth + 1)
    visit(reader.trailer)


def validate_upload(upload, field):
    extension = Path(upload.name).suffix.lower().lstrip('.')
    expected = ALLOWED.get(extension)
    if not expected or extension not in field['allowed_extensions']:
        raise ValidationError('File extension is not allowed.')
    if upload.content_type != expected:
        raise ValidationError('Declared content type does not match the allowed file type.')
    if not 0 < upload.size <= min(field['max_file_size'], 10 * 1024 * 1024):
        raise ValidationError('File is empty or exceeds the size limit.')
    upload.seek(0)
    data = upload.read(10 * 1024 * 1024 + 1)
    upload.seek(0)
    if len(data) != upload.size:
        raise ValidationError('Invalid file size.')
    try:
        if extension == 'pdf':
            check_pdf(data)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    if image.format != ('PNG' if extension == 'png' else 'JPEG') or image.width * image.height > 16000000:
                        raise ValueError('Image format or dimensions unsupported')
                    image.verify()
                with Image.open(BytesIO(data)) as image:
                    image.load()
                    # Re-encode to drop EXIF, untrusted metadata and appended payloads.
                    clean = image.convert('RGBA' if extension == 'png' and 'A' in image.getbands() else 'RGB')
                    clean.info.clear()
                    output = BytesIO()
                    clean.save(output, format='PNG' if extension == 'png' else 'JPEG')
                    data = output.getvalue()
    except Exception:
        # Parser messages may contain document content; never include them in API/log output.
        raise ValidationError('File content is invalid or unsupported.') from None
    if len(data) > field['max_file_size']:
        raise ValidationError('Sanitized image exceeds the configured size limit.')
    return SimpleUploadedFile(safe_filename(upload.name), data, content_type=expected)
