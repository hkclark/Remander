"""Tests for command history and detail routes."""

from httpx import AsyncClient

from remander.models.enums import ActivityStatus, CommandStatus, CommandType
from remander.services.activity import log_activity
from tests.factories import create_command


class TestCommandHistory:
    async def test_get_command_list(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/commands")
        assert response.status_code == 200
        assert "Command History" in response.text

    async def test_shows_commands(self, logged_in_client: AsyncClient) -> None:
        await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        response = await logged_in_client.get("/commands")
        assert "set_away_now" in response.text

    async def test_pagination_page_2(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/commands?page=2")
        assert response.status_code == 200


class TestCommandDetail:
    async def test_get_command_detail(self, logged_in_client: AsyncClient) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_HOME_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        response = await logged_in_client.get(f"/commands/{cmd.id}")
        assert response.status_code == 200
        assert "set_home_now" in response.text

    async def test_command_not_found(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/commands/999")
        assert response.status_code == 404

    async def test_detail_shows_activity_log(self, logged_in_client: AsyncClient) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        await log_activity(
            command_id=cmd.id,
            step_name="NVRLoginNode",
            status=ActivityStatus.SUCCEEDED,
        )
        response = await logged_in_client.get(f"/commands/{cmd.id}")
        assert "NVRLoginNode" in response.text
