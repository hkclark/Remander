"""Email notification sender — aiosmtplib implementation."""

from email.message import EmailMessage

import aiosmtplib
import attrs


@attrs.define
class EmailNotificationSender:
    """Sends email notifications via SMTP using aiosmtplib."""

    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_to: str
    smtp_use_tls: bool = True

    async def send(
        self,
        subject: str,
        body: str,
        *,
        html_body: str | None = None,
    ) -> None:
        """Send an email notification."""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_from
        msg["To"] = self.smtp_to
        msg.set_content(body)

        if html_body is not None:
            msg.add_alternative(html_body, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_username,
            password=self.smtp_password,
            start_tls=self.smtp_use_tls,
        )
