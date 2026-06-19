"""Cloudinary Cloud Media Pipeline — FRD §2C."""
import io
import uuid
from pathlib import Path
# pyrefly: ignore [missing-import]
from django.conf import settings
# pyrefly: ignore [missing-import]
import cloudinary
# pyrefly: ignore [missing-import]
import cloudinary.uploader

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

CLOUD_ENABLED = bool(settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET)


def upload_to_cloud(image_bytes: bytes, original_name: str) -> str:
    if not CLOUD_ENABLED:
        ext = Path(original_name).suffix.lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_dir = Path(settings.MEDIA_ROOT)
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / filename).write_bytes(image_bytes)
        return f'/uploads/{filename}'

    result = cloudinary.uploader.upload(
        io.BytesIO(image_bytes),
        folder='aqi_reports',
        resource_type='image',
        allowed_formats=['jpg', 'jpeg', 'png', 'webp', 'gif'],
        transformation=[{'quality': 'auto', 'fetch_format': 'auto'}],
    )
    return result['secure_url']
