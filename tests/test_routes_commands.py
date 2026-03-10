"""Tests for command execution and management routes."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from remander.models.enums import CommandStatus, CommandType
from tests.factories import create_command, create_tag


class TestCommandExecutePage:
    async def test_get_execute_page(self, client: AsyncClient) -> None:
        response = await client.get("/commands/execute")
        assert response.status_code == 200
        assert "Set Away Now" in response.text
        assert "Set Home Now" in response.text


class TestCommandExecution:
    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_set_away_now(self, mock_enqueue: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/commands/execute/set-away-now",
            follow_redirects=False,
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_set_away_delayed(self, mock_enqueue: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/commands/execute/set-away-delayed",
            data={"delay_minutes": "15"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_set_home_now(self, mock_enqueue: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/commands/execute/set-home-now",
            follow_redirects=False,
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_pause_notifications(self, mock_enqueue: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/commands/execute/pause-notifications",
            data={"pause_minutes": "30"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_pause_recording(self, mock_enqueue: AsyncMock, client: AsyncClient) -> None:
        response = await client.post(
            "/commands/execute/pause-recording",
            data={"pause_minutes": "60"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_records_initiated_by_ip(
        self, mock_enqueue: AsyncMock, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/commands/execute/set-away-now",
            follow_redirects=False,
        )
        assert response.status_code == 303

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_records_initiated_by_user(
        self, mock_enqueue: AsyncMock, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/commands/execute/set-away-now?user=testuser",
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestEmptyTagValidation:
    async def test_pause_notifications_empty_tag_returns_422(
        self, client: AsyncClient
    ) -> None:
        await create_tag(name="empty-tag")
        response = await client.post(
            "/commands/execute/pause-notifications",
            data={"pause_minutes": "30", "tag_filter": "empty-tag"},
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "empty-tag" in response.text

    async def test_pause_recording_empty_tag_returns_422(
        self, client: AsyncClient
    ) -> None:
        await create_tag(name="empty-tag")
        response = await client.post(
            "/commands/execute/pause-recording",
            data={"pause_minutes": "60", "tag_filter": "empty-tag"},
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "empty-tag" in response.text


class TestCommandCancel:
    async def test_cancel_pending_command(self, client: AsyncClient) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.PENDING,
        )
        response = await client.post(
            f"/commands/{cmd.id}/cancel",
            follow_redirects=False,
        )
        assert response.status_code == 303
