from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_WIDTH = 1600


class ImageValidationError(ValueError):
    pass


@dataclass(slots=True)
class ProcessedImage:
    original_filename: str
    stored_filename: str
    url_path: str
    sort_order: int


def _choose_output(image: Image.Image) -> tuple[Image.Image, str, str, dict]:
    has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
    if has_alpha:
        converted = image.convert("RGBA")
        return converted, "WEBP", ".webp", {"quality": 84, "method": 6}

    converted = image.convert("RGB")
    return converted, "JPEG", ".jpg", {"quality": 84, "optimize": True}


async def process_uploads(files: list[UploadFile]) -> list[ProcessedImage]:
    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        raise ImageValidationError("Add at least one photo so Chicago can judge the damage.")
    if len(valid_files) > settings.max_images_per_pothole:
        raise ImageValidationError(f"You can upload up to {settings.max_images_per_pothole} images per pothole.")

    saved: list[ProcessedImage] = []
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    for index, upload in enumerate(valid_files):
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ImageValidationError("Use JPG, PNG, or WEBP images only.")
        if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
            raise ImageValidationError("That file does not look like a supported image.")

        raw = await upload.read()
        if len(raw) > settings.max_upload_bytes:
            raise ImageValidationError(
                f"Each image must be under {settings.max_upload_mb}MB."
            )

        try:
            image = Image.open(BytesIO(raw))
            image.load()
        except UnidentifiedImageError as exc:
            raise ImageValidationError("One of the uploaded files could not be read as an image.") from exc

        image = ImageOps.exif_transpose(image)
        if image.width > MAX_WIDTH:
            new_height = int(image.height * (MAX_WIDTH / image.width))
            image = image.resize((MAX_WIDTH, new_height))

        prepared, fmt, out_suffix, save_kwargs = _choose_output(image)
        stored_filename = f"{uuid4().hex}{out_suffix}"
        destination = settings.upload_path / stored_filename
        prepared.save(destination, format=fmt, **save_kwargs)

        saved.append(
            ProcessedImage(
                original_filename=upload.filename,
                stored_filename=stored_filename,
                url_path=f"/static/uploads/{stored_filename}",
                sort_order=index,
            )
        )

    return saved
