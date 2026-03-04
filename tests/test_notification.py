"""Tests for the notification system — RED phase (TDD)."""

from unittest.mock import AsyncMock, patch

from remander.clients.email import EmailNotificationSender
from remander.models.enums import CommandStatus, CommandType
from remander.services.notification import NotificationSender
from remander.services.notification_templates import (
    render_command_failed_notification,
    render_command_succeeded_notification,
    render_completed_with_errors_notification,
    render_validation_warnings_notification,
)
from tests.factories import create_command


class TestNotificationSenderProtocol:
    async def test_email_sender_satisfies_protocol(self) -> None:
        """EmailNotificationSender must satisfy the NotificationSender protocol."""
        sender = EmailNotificationSender(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
            smtp_from="from@example.com",
            smtp_to="to@example.com",
            smtp_use_tls=True,
        )
        # Protocol conformance check at runtime
        assert isinstance(sender, NotificationSender)


class TestEmailNotificationSender:
    async def test_send_plain_text(self) -> None:
        """send() should call aiosmtplib to deliver the email."""
        sender = EmailNotificationSender(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
            smtp_from="from@example.com",
            smtp_to="to@example.com",
            smtp_use_tls=True,
        )
        with patch("remander.clients.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await sender.send("Test Subject", "Test body")
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args
            # The message should be an email.message.EmailMessage
            msg = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("message")
            assert msg["Subject"] == "Test Subject"
            assert msg["From"] == "from@example.com"
            assert msg["To"] == "to@example.com"

    async def test_send_with_html_body(self) -> None:
        """send() with html_body should create a multipart email."""
        sender = EmailNotificationSender(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
            smtp_from="from@example.com",
            smtp_to="to@example.com",
            smtp_use_tls=True,
        )
        with patch("remander.clients.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await sender.send("HTML Test", "Plain body", html_body="<h1>HTML body</h1>")
            mock_send.assert_called_once()


class TestNotificationTemplates:
    async def test_render_succeeded(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        subject, body = render_command_succeeded_notification(cmd, device_count=5, duration_s=12.5)
        assert "Set Away Now" in subject or "set_away_now" in subject.lower()
        assert "5" in body
        assert subject  # non-empty

    async def test_render_failed(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.FAILED,
        )
        subject, body = render_command_failed_notification(
            cmd, error="NVR login failed", failed_step="nvr_login"
        )
        assert "failed" in subject.lower() or "Failed" in subject
        assert "NVR login failed" in body

    async def test_render_completed_with_errors(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.COMPLETED_WITH_ERRORS,
        )
        successes = [{"device": "Cam 1", "detail": "OK"}]
        failures = [{"device": "Cam 2", "detail": "Timeout"}]
        subject, body = render_completed_with_errors_notification(cmd, successes, failures)
        assert subject  # non-empty
        assert "Cam 2" in body
        assert "Timeout" in body

    async def test_render_validation_warnings(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        discrepancies = [
            {
                "device": "Cam 1",
                "expected": "111111111111111111111111",
                "actual": "000000000000000000000000",
            }
        ]
        subject, body = render_validation_warnings_notification(cmd, discrepancies)
        assert "validation" in subject.lower() or "warning" in subject.lower()
        assert "Cam 1" in body
