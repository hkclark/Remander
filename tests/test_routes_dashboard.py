"""Tests for dashboard routes."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from remander.models.enums import CommandStatus, CommandType
from remander.models.state import AppState
from remander.services.tag import create_tag
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

    async def test_command_progress_partial_no_active(self, client: AsyncClient) -> None:
        response = await client.get("/partials/command-progress")
        assert response.status_code == 286


class TestDashboardAwayButtons:
    async def test_shows_set_away_delayed_buttons(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert "Set Away in 3 Min" in response.text
        assert "Set Away in 5 Min" in response.text

    async def test_set_away_delayed_posts_delay_minutes(self, client: AsyncClient) -> None:
        response = await client.post(
            "/commands/execute/set-away-delayed",
            data={"delay_minutes": "3"},
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestDashboardDebugMode:
    @patch("remander.routes.dashboard.get_settings")
    async def test_shows_1min_pause_in_debug_mode(
        self, mock_settings: AsyncMock, client: AsyncClient
    ) -> None:
        from remander.config import Settings

        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        settings.debug = True
        mock_settings.return_value = settings
        await create_tag("test-tag", show_on_dashboard=True)
        response = await client.get("/")
        assert "1 Min" in response.text

    async def test_hides_1min_pause_without_debug(self, client: AsyncClient) -> None:
        await create_tag("test-tag", show_on_dashboard=True)
        response = await client.get("/")
        assert "1 Min" not in response.text
        assert "3 Min" in response.text


class TestDashboardPauseNotifications:
    async def test_shows_pause_section_for_dashboard_tags(self, client: AsyncClient) -> None:
        await create_tag("driveway", show_on_dashboard=True)
        response = await client.get("/")
        assert "driveway" in response.text
        assert "Pause Notifications" in response.text

    async def test_hides_non_dashboard_tags(self, client: AsyncClient) -> None:
        await create_tag("hidden-tag", show_on_dashboard=False)
        response = await client.get("/")
        assert "hidden-tag" not in response.text

    async def test_shows_time_period_buttons(self, client: AsyncClient) -> None:
        await create_tag("patio", show_on_dashboard=True)
        response = await client.get("/")
        assert "3 Min" in response.text
        assert "15 Min" in response.text
        assert "30 Min" in response.text
        assert "1 Hour" in response.text
        assert "2 Hours" in response.text

    async def test_no_pause_section_when_no_dashboard_tags(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert "Pause Notifications" not in response.text
