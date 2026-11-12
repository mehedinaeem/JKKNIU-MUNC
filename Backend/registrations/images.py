"""Bounded private image previews, re-encoded without original metadata."""
from io import BytesIO
import warnings
from PIL import Image, ImageOps


def image_preview(source, provider, content_type, large=False):
    limit = 10 * 1024 * 1024
    try:
        if provider == 'cloudinary':
            output = BytesIO()
            for chunk in source.iter_content(chunk_size=64 * 1024):
                if output.tell() + len(chunk) > limit:
                    raise ValueError('Image exceeds preview limit')
                output.write(chunk)
            data = output.getvalue()
        else:
            data = source.read(limit + 1)
    finally:
        source.close()
    if not data or len(data) > limit:
        raise ValueError('Invalid image size')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            expected = 'PNG' if content_type == 'image/png' else 'JPEG'
            if image.format != expected or image.width * image.height > 16000000:
                raise ValueError('Unsupported image')
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((1200, 1200) if large else (160, 160))
            clean = image.convert('RGBA' if expected == 'PNG' and 'A' in image.getbands() else 'RGB')
            clean.info.clear()
            output = BytesIO()
            clean.save(output, format=expected)
    return output.getvalue()
