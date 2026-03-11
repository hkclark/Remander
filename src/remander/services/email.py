"""Auth email helper — sends to a user's own address (not the admin smtp_to)."""

import logging

from remander.clients.email import EmailNotificationSender
from remander.config import get_settings

logger = logging.getLogger(__name__)


async def send_auth_email(to: str, subject: str, body: str) -> None:
    """Send an auth email (password reset / invitation) to the given address.

    Uses the configured SMTP settings but sends to `to` instead of `smtp_to`.
    Logs and swallows errors so a failed send never crashes an auth flow.
    """
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping auth email to %s", to)
        return

    sender = EmailNotificationSender(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password.get_secret_value(),
        smtp_from=settings.smtp_from or settings.smtp_username,
        smtp_to=to,
        smtp_use_tls=settings.smtp_use_tls,
    )
    try:
        await sender.send(subject=subject, body=body)
        logger.info("Auth email sent to %s: %s", to, subject)
    except Exception:
        logger.exception("Failed to send auth email to %s", to)
