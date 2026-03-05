"""Tests for admin routes."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from remander.models.enums import CommandStatus, CommandType
from tests.factories import create_command


class TestAdminPage:
    async def test_get_admin_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/admin")
        assert response.status_code == 200
        assert "Admin" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_nvr(self, mock_nvr_cls: AsyncMock, client: AsyncClient) -> None:
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {"channel": 0, "name": "Front", "online": True},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await client.post("/admin/query-nvr", follow_redirects=False)
        # Should redirect or render result
        assert response.status_code in (200, 303)

    async def test_pending_jobs_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/admin/pending-jobs")
        assert response.status_code == 200

    async def test_audit_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/admin/audit")
        assert response.status_code == 200

    async def test_audit_shows_commands(self, client: AsyncClient) -> None:
        await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        response = await client.get("/admin/audit")
        assert "set_away_now" in response.text
