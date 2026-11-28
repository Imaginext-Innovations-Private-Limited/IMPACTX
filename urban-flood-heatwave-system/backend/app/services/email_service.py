
"""Email notification service using Gmail SMTP."""

import logging
import smtplib
import asyncio
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:

    def _send_email_sync(self, recipient: str, subject: str, body: str):
        if not settings.EMAIL_ENABLED:
            logger.info("Email notifications are disabled.")
            return False

        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.error("Email credentials are not configured.")
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        message["To"] = recipient
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()

                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD,
                )

                server.send_message(message)

            logger.info("Alert email sent to %s", recipient)
            return True

        except Exception:
            logger.exception("Failed to send email to %s", recipient)
            return False

    async def send_email(self, recipient: str, subject: str, body: str):
        """Send email without blocking the asynchronous backend."""
        return await asyncio.to_thread(
            self._send_email_sync,
            recipient,
            subject,
            body,
        )


email_service = EmailService()
