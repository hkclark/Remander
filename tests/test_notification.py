"""Tests for the notification system."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from remander.clients.email import EmailNotificationSender
from remander.models.enums import CommandStatus, CommandType
from remander.services.notification import NotificationSender
from remander.services.notification_templates import render_notification
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
    async def test_subject_pass_with_channels(self) -> None:
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            status=CommandStatus.SUCCEEDED,
        )
        subject, _ = render_notification(
            command=cmd,
            channel_bitmask_results={6: {"motion": "0" * 24, "person": "1" * 24}},
            validation_discrepancies=[],
            overall_pass=True,
        )
        assert subject == "PASS: Pause Notifications - Channels: [6]"

    async def test_subject_fail_multiple_channels(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.FAILED,
        )
        subject, _ = render_notification(
            command=cmd,
            channel_bitmask_results={
                2: {"motion": "0" * 24},
                5: {"motion": "1" * 24},
                11: {"motion": "1" * 24},
            },
            validation_discrepancies=[],
            overall_pass=False,
        )
        assert subject == "FAIL: Set Away Now - Channels: [2, 5, 11]"

    async def test_subject_empty_channels(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.FAILED,
        )
        subject, _ = render_notification(
            command=cmd,
            channel_bitmask_results={},
            validation_discrepancies=[],
            overall_pass=False,
            error_message="NVR login failed",
        )
        assert subject == "FAIL: Set Away Now - Channels: []"

    async def test_body_header_section(self) -> None:
        now = datetime(2026, 3, 9, 14, 35, 12, tzinfo=timezone.utc)
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            status=CommandStatus.SUCCEEDED,
        )
        cmd.started_at = now
        cmd.completed_at = now
        cmd.initiated_by_ip = "192.168.1.101"
        subject, body = render_notification(
            command=cmd,
            channel_bitmask_results={},
            validation_discrepancies=[],
            overall_pass=True,
        )
        assert "Overall: PASS" in body
        assert "Pause Notifications" in body
        assert "N/A (192.168.1.101)" in body
        assert "Start Time:" in body
        assert "Finish Time:" in body

    async def test_body_bitmask_visual_display(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        subject, body = render_notification(
            command=cmd,
            channel_bitmask_results={
                6: {
                    "motion": "0" * 24,
                    "person": "1" * 24,
                }
            },
            validation_discrepancies=[],
            overall_pass=True,
        )
        assert "channel=6:" in body
        # motion → MD, displayed as dots
        assert "MD" in body
        assert "." * 24 in body
        # person displayed as pipes
        assert "person" in body
        assert "|" * 24 in body

    async def test_body_bitmask_ok_and_fail_status(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.COMPLETED_WITH_ERRORS,
        )
        subject, body = render_notification(
            command=cmd,
            channel_bitmask_results={
                6: {"motion": "0" * 24, "person": "1" * 24},
            },
            validation_discrepancies=[
                {"channel": 6, "detection_type": "person", "device": "Cam", "device_id": 1}
            ],
            overall_pass=False,
        )
        assert "OK" in body
        assert "FAIL" in body

    async def test_body_error_message_included(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.FAILED,
        )
        _, body = render_notification(
            command=cmd,
            channel_bitmask_results={},
            validation_discrepancies=[],
            overall_pass=False,
            error_message="NVR login timed out",
        )
        assert "NVR login timed out" in body

    async def test_body_rearm_label(self) -> None:
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            status=CommandStatus.SUCCEEDED,
        )
        subject, body = render_notification(
            command=cmd,
            channel_bitmask_results={6: {"motion": "1" * 24}},
            validation_discrepancies=[],
            overall_pass=True,
            is_rearm=True,
        )
        assert "Re-arm" in subject
        assert "Re-arm" in body

    async def test_motion_sorted_last_ai_types_first(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        _, body = render_notification(
            command=cmd,
            channel_bitmask_results={
                6: {
                    "motion": "0" * 24,
                    "person": "1" * 24,
                    "vehicle": "1" * 24,
                }
            },
            validation_discrepancies=[],
            overall_pass=True,
        )
        # MD should appear after person and vehicle in the output
        person_pos = body.index("person")
        vehicle_pos = body.index("vehicle")
        md_pos = body.index("MD")
        assert person_pos < md_pos
        assert vehicle_pos < md_pos
