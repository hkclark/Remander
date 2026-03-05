"""Tests for activity log routes."""

from httpx import AsyncClient

from remander.models.enums import ActivityStatus, CommandStatus, CommandType
from remander.services.activity import log_activity
from tests.factories import create_camera, create_command


class TestActivityLog:
    async def test_get_activity_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/activity")
        assert response.status_code == 200
        assert "Activity" in response.text

    async def test_shows_activity_entries(self, client: AsyncClient) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        await log_activity(
            command_id=cmd.id,
            step_name="NVRLoginNode",
            status=ActivityStatus.SUCCEEDED,
        )
        response = await client.get("/activity")
        assert "NVRLoginNode" in response.text

    async def test_filter_by_command_id(self, client: AsyncClient) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        await log_activity(
            command_id=cmd.id,
            step_name="FilterNode",
            status=ActivityStatus.SUCCEEDED,
        )
        response = await client.get(f"/activity?command_id={cmd.id}")
        assert response.status_code == 200
        assert "FilterNode" in response.text

    async def test_filter_by_device_id(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Log Cam")
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        await log_activity(
            command_id=cmd.id,
            step_name="SetBitmask",
            status=ActivityStatus.SUCCEEDED,
            device_id=cam.id,
        )
        response = await client.get(f"/activity?device_id={cam.id}")
        assert response.status_code == 200
        assert "SetBitmask" in response.text

    async def test_filter_by_status(self, client: AsyncClient) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.FAILED,
        )
        await log_activity(
            command_id=cmd.id,
            step_name="FailedStep",
            status=ActivityStatus.FAILED,
        )
        response = await client.get("/activity?status=failed")
        assert response.status_code == 200
        assert "FailedStep" in response.text
