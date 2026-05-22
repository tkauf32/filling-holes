from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    return int(value)


@dataclass(slots=True)
class Settings:
    app_name: str
    app_env: str
    app_base_url: str
    database_url: str
    admin_password: str
    secret_key: str
    upload_dir: str
    max_images_per_pothole: int
    max_upload_mb: int
    chicago_only: bool
    admin_notification_email: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str

    @property
    def upload_path(self) -> Path:
        return BASE_DIR / self.upload_dir

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "FillingHoles.com"),
        app_env=os.getenv("APP_ENV", "development"),
        app_base_url=os.getenv("APP_BASE_URL", "http://localhost:6969"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/fillingholes.db"),
        admin_password=os.getenv("ADMIN_PASSWORD", "change-me-tonight"),
        secret_key=os.getenv("SECRET_KEY", "change-this-dev-secret"),
        upload_dir=os.getenv("UPLOAD_DIR", "app/static/uploads"),
        max_images_per_pothole=_to_int(os.getenv("MAX_IMAGES_PER_POTHOLE"), 3),
        max_upload_mb=_to_int(os.getenv("MAX_UPLOAD_MB"), 8),
        chicago_only=_to_bool(os.getenv("CHICAGO_ONLY"), True),
        admin_notification_email=os.getenv("ADMIN_NOTIFICATION_EMAIL", ""),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=_to_int(os.getenv("SMTP_PORT"), 587),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", ""),
    )


settings = get_settings()
