"""Tests for dashboard routes."""

from httpx import AsyncClient

from remander.models.enums import CommandStatus, CommandType
from remander.models.state import AppState
from tests.factories import create_command


class TestDashboard:
    async def test_get_dashboard(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Remander" in response.text

    async def test_shows_current_mode(self, client: AsyncClient) -> None:
        await AppState.create(key="current_mode", value="away")
        response = await client.get("/")
        assert response.status_code == 200
        assert "Away" in response.text

    async def test_shows_home_mode(self, client: AsyncClient) -> None:
        await AppState.create(key="current_mode", value="home")
        response = await client.get("/")
        assert "Home" in response.text

    async def test_shows_last_command(self, client: AsyncClient) -> None:
        await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        response = await client.get("/")
        assert response.status_code == 200
        assert "set_away_now" in response.text

    async def test_shows_quick_action_buttons(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert "Set Away Now" in response.text
        assert "Set Home Now" in response.text

    async def test_command_progress_partial(self, client: AsyncClient) -> None:
        response = await client.get("/partials/command-progress")
        assert response.status_code == 200
