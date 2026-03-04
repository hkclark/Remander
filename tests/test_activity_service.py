"""Tests for the activity logging service — RED phase (TDD)."""

from remander.models.enums import ActivityStatus
from remander.services.activity import (
    get_activities_for_command,
    get_activities_for_device,
    log_activity,
    update_activity_status,
)
from tests.factories import create_camera, create_command


class TestLogActivity:
    async def test_log_basic(self) -> None:
        cmd = await create_command()
        entry = await log_activity(
            command_id=cmd.id,
            step_name="nvr_login",
            status=ActivityStatus.STARTED,
        )
        assert entry.id is not None
        assert entry.command_id == cmd.id
        assert entry.step_name == "nvr_login"
        assert entry.status == ActivityStatus.STARTED
        assert entry.device_id is None

    async def test_log_with_device(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Log Cam")
        entry = await log_activity(
            command_id=cmd.id,
            device_id=camera.id,
            step_name="set_bitmask",
            status=ActivityStatus.SUCCEEDED,
        )
        assert entry.device_id == camera.id

    async def test_log_with_detail_and_duration(self) -> None:
        cmd = await create_command()
        entry = await log_activity(
            command_id=cmd.id,
            step_name="power_on",
            status=ActivityStatus.FAILED,
            detail="Timeout waiting for camera",
            duration_ms=5000,
        )
        assert entry.detail == "Timeout waiting for camera"
        assert entry.duration_ms == 5000

    async def test_log_without_device(self) -> None:
        """Non-device-specific steps (like NVR login) have device_id=None."""
        cmd = await create_command()
        entry = await log_activity(
            command_id=cmd.id,
            step_name="nvr_login",
            status=ActivityStatus.STARTED,
        )
        assert entry.device_id is None


class TestGetActivitiesForCommand:
    async def test_get_all_for_command(self) -> None:
        cmd = await create_command()
        await log_activity(command_id=cmd.id, step_name="step1", status=ActivityStatus.SUCCEEDED)
        await log_activity(command_id=cmd.id, step_name="step2", status=ActivityStatus.SUCCEEDED)

        result = await get_activities_for_command(cmd.id)
        assert len(result) == 2

    async def test_ordered_by_created_at(self) -> None:
        cmd = await create_command()
        e1 = await log_activity(
            command_id=cmd.id, step_name="first", status=ActivityStatus.SUCCEEDED
        )
        e2 = await log_activity(
            command_id=cmd.id, step_name="second", status=ActivityStatus.SUCCEEDED
        )

        result = await get_activities_for_command(cmd.id)
        assert result[0].id == e1.id
        assert result[1].id == e2.id

    async def test_empty_result(self) -> None:
        result = await get_activities_for_command(99999)
        assert result == []


class TestGetActivitiesForDevice:
    async def test_get_across_commands(self) -> None:
        camera = await create_camera(name="Activity Cam")
        cmd1 = await create_command()
        cmd2 = await create_command()

        await log_activity(
            command_id=cmd1.id,
            device_id=camera.id,
            step_name="set_bitmask",
            status=ActivityStatus.SUCCEEDED,
        )
        await log_activity(
            command_id=cmd2.id,
            device_id=camera.id,
            step_name="set_bitmask",
            status=ActivityStatus.FAILED,
        )

        result = await get_activities_for_device(camera.id)
        assert len(result) == 2


class TestUpdateActivityStatus:
    async def test_update_to_succeeded(self) -> None:
        cmd = await create_command()
        entry = await log_activity(
            command_id=cmd.id, step_name="nvr_login", status=ActivityStatus.STARTED
        )
        updated = await update_activity_status(entry.id, ActivityStatus.SUCCEEDED, duration_ms=150)
        assert updated is not None
        assert updated.status == ActivityStatus.SUCCEEDED
        assert updated.duration_ms == 150

    async def test_update_to_failed_with_detail(self) -> None:
        cmd = await create_command()
        entry = await log_activity(
            command_id=cmd.id, step_name="power_on", status=ActivityStatus.STARTED
        )
        updated = await update_activity_status(
            entry.id, ActivityStatus.FAILED, detail="Connection refused"
        )
        assert updated is not None
        assert updated.status == ActivityStatus.FAILED
        assert updated.detail == "Connection refused"

    async def test_update_nonexistent(self) -> None:
        result = await update_activity_status(99999, ActivityStatus.SUCCEEDED)
        assert result is None
