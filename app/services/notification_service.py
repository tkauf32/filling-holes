from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings
from app.models import Pothole


def notify_admin_new_submission(pothole: Pothole) -> None:
    subject = f"New pothole submitted: {pothole.public_id}"
    body = (
        f"New pothole report received.\n\n"
        f"ID: {pothole.public_id}\n"
        f"Severity: {pothole.severity}\n"
        f"Coordinates: {pothole.latitude}, {pothole.longitude}\n"
        f"Description: {pothole.description or 'n/a'}\n"
    )

    smtp_ready = all(
        [settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from, settings.admin_notification_email]
    )
    if not smtp_ready:
        print(f"[notify_admin] {subject}\n{body}")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = settings.admin_notification_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
