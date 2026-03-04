"""Tests for validation service — RED phase (TDD)."""

from unittest.mock import AsyncMock

from remander.models.enums import CommandStatus, DetectionType
from remander.services.validation import validate_command_results, validate_device_bitmasks
from tests.factories import create_camera, create_command


class TestValidateDeviceBitmasks:
    async def test_returns_empty_when_all_match(self) -> None:
        camera = await create_camera(name="Match Cam", channel=0)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "111111111111111111111111"
        nvr_client.get_detection_zones.return_value = "0" * 4800

        expected = {
            DetectionType.MOTION: {
                "hour_bitmask": "111111111111111111111111",
                "zone_mask": "0" * 4800,
            }
        }

        discrepancies = await validate_device_bitmasks(camera, expected, nvr_client)
        assert discrepancies == []

    async def test_detects_hour_bitmask_mismatch(self) -> None:
        camera = await create_camera(name="Mismatch Cam", channel=1)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "000000000000000000000000"
        nvr_client.get_detection_zones.return_value = "0" * 4800

        expected = {
            DetectionType.MOTION: {
                "hour_bitmask": "111111111111111111111111",
                "zone_mask": "0" * 4800,
            }
        }

        discrepancies = await validate_device_bitmasks(camera, expected, nvr_client)
        assert len(discrepancies) == 1
        assert discrepancies[0]["field"] == "hour_bitmask"
        assert discrepancies[0]["expected"] == "111111111111111111111111"
        assert discrepancies[0]["actual"] == "000000000000000000000000"
        assert discrepancies[0]["device"] == "Mismatch Cam"

    async def test_detects_zone_mask_mismatch(self) -> None:
        camera = await create_camera(name="Zone Cam", channel=2)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "111111111111111111111111"
        nvr_client.get_detection_zones.return_value = "1" * 4800

        expected = {
            DetectionType.MOTION: {
                "hour_bitmask": "111111111111111111111111",
                "zone_mask": "0" * 4800,
            }
        }

        discrepancies = await validate_device_bitmasks(camera, expected, nvr_client)
        assert len(discrepancies) == 1
        assert discrepancies[0]["field"] == "zone_mask"

    async def test_detects_multiple_mismatches(self) -> None:
        camera = await create_camera(name="Multi Cam", channel=3)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "000000000000000000000000"
        nvr_client.get_detection_zones.return_value = "1" * 4800

        expected = {
            DetectionType.MOTION: {
                "hour_bitmask": "111111111111111111111111",
                "zone_mask": "0" * 4800,
            }
        }

        discrepancies = await validate_device_bitmasks(camera, expected, nvr_client)
        assert len(discrepancies) == 2

    async def test_skips_device_without_channel(self) -> None:
        camera = await create_camera(name="No Channel Cam", channel=None)
        nvr_client = AsyncMock()

        expected = {
            DetectionType.MOTION: {
                "hour_bitmask": "111111111111111111111111",
                "zone_mask": "0" * 4800,
            }
        }

        discrepancies = await validate_device_bitmasks(camera, expected, nvr_client)
        assert discrepancies == []
        nvr_client.get_alarm_schedule.assert_not_called()


class TestValidateCommandResults:
    async def test_logs_discrepancies_to_activity(self) -> None:
        cmd = await create_command(status=CommandStatus.RUNNING)
        camera = await create_camera(name="Log Cam", channel=0)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "000000000000000000000000"
        nvr_client.get_detection_zones.return_value = "0" * 4800

        expected_bitmasks = {
            camera.id: {
                DetectionType.MOTION: {
                    "hour_bitmask": "111111111111111111111111",
                    "zone_mask": "0" * 4800,
                }
            }
        }

        discrepancies = await validate_command_results(cmd.id, expected_bitmasks, nvr_client)
        assert len(discrepancies) == 1

    async def test_returns_empty_when_all_match(self) -> None:
        cmd = await create_command(status=CommandStatus.RUNNING)
        camera = await create_camera(name="OK Cam", channel=0)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "111111111111111111111111"
        nvr_client.get_detection_zones.return_value = "0" * 4800

        expected_bitmasks = {
            camera.id: {
                DetectionType.MOTION: {
                    "hour_bitmask": "111111111111111111111111",
                    "zone_mask": "0" * 4800,
                }
            }
        }

        discrepancies = await validate_command_results(cmd.id, expected_bitmasks, nvr_client)
        assert discrepancies == []

    async def test_does_not_change_command_status(self) -> None:
        """Validation discrepancies are warnings, not status changes."""
        cmd = await create_command(status=CommandStatus.RUNNING)
        camera = await create_camera(name="Status Cam", channel=0)
        nvr_client = AsyncMock()
        nvr_client.get_alarm_schedule.return_value = "000000000000000000000000"
        nvr_client.get_detection_zones.return_value = "0" * 4800

        expected_bitmasks = {
            camera.id: {
                DetectionType.MOTION: {
                    "hour_bitmask": "111111111111111111111111",
                    "zone_mask": "0" * 4800,
                }
            }
        }

        await validate_command_results(cmd.id, expected_bitmasks, nvr_client)

        from remander.models.command import Command

        updated = await Command.get(id=cmd.id)
        assert updated.status == CommandStatus.RUNNING  # unchanged
