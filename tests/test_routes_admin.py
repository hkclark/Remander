"""Tests for admin routes."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from remander.models.device import Device
from remander.models.enums import CommandStatus, CommandType, DetectionType
from remander.services.detection import set_detection_types
from tests.factories import create_camera, create_command


class TestAdminPage:
    async def test_get_admin_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin")
        assert response.status_code == 200
        assert "Admin" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_nvr(self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient) -> None:
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {"channel": 0, "name": "Front", "online": True},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr", follow_redirects=False)
        # Should redirect or render result
        assert response.status_code in (200, 303)

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_nvr_timeout_returns_error(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.login.side_effect = asyncio.TimeoutError
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert response.status_code == 200
        assert "timed out" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_nvr_connection_error_returns_error(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.login.side_effect = ConnectionError("Connection refused")
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert response.status_code == 200
        assert "Connection refused" in response.text

    async def test_pending_jobs_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin/pending-jobs")
        assert response.status_code == 200

    async def test_audit_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin/audit")
        assert response.status_code == 200

    async def test_audit_shows_commands(self, logged_in_client: AsyncClient) -> None:
        await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
        )
        response = await logged_in_client.get("/admin/audit")
        assert "set_away_now" in response.text


class TestQueryNvrWithComparison:
    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_new_channel_shows_new_badge(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert response.status_code == 200
        assert "New" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_changed_channel_shows_changed_badge(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        await create_camera(
            name="OldName", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {
                "channel": 0,
                "name": "NewName",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert response.status_code == 200
        assert "Changed" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_ok_channel_shows_ok_badge(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        await create_camera(
            name="Front", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert response.status_code == 200
        assert "OK" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_add_update_all_visible_when_actionable(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert "Add/Update All" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_add_update_all_hidden_when_all_ok(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        await create_camera(
            name="Front", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        mock_client = AsyncMock()
        mock_client.list_channels.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-nvr")
        assert "Add/Update All" not in response.text


class TestQueryPushSchedules:
    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_schedules_returns_200(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "table": {
                    "MD": "1" * 168,
                    "AI_PEOPLE": "0" * 168,
                },
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert response.status_code == 200
        assert "Front" in response.text
        assert "Motion Detection" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_schedules_shows_detection_types(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "table": {
                    "MD": "1" * 168,
                    "AI_PEOPLE": "0" * 168,
                    "AI_VEHICLE": "0" * 168,
                },
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Person (AI)" in response.text
        assert "Vehicle (AI)" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_friendly_label_for_md(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {"channel": 0, "name": "Front", "table": {"MD": "1" * 168}},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Motion Detection" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_no_toggle_when_table_fully_shown(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        """Single-key table → summary equals full table → no toggle needed."""
        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {"channel": 0, "name": "Front", "table": {"MD": "1" * 168}},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Show all" not in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_toggle_appears_for_unconfigured_camera_with_ai_keys(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        """Camera with no detection types configured → defaults to first AI key → toggle shown."""
        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {"channel": 0, "name": "Front", "table": {"MD": "1" * 168, "AI_PEOPLE": "0" * 168}},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Person (AI)" in response.text
        assert "Show all" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_toggle_shown_when_device_has_fewer_summary_keys(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        """Device with MOTION only → summary shows MD; NVR also has AI_PEOPLE → toggle shown."""
        camera = await create_camera(channel=0)
        await set_detection_types(camera.id, [DetectionType.MOTION])

        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {"channel": 0, "name": "Front", "table": {"MD": "1" * 168, "AI_PEOPLE": "0" * 168}},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Show all" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_ai_only_device_shows_ai_label_in_summary(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        """Device with PERSON only → summary key is AI_PEOPLE → 'Person (AI)' shown, toggle present."""
        camera = await create_camera(channel=0)
        await set_detection_types(camera.id, [DetectionType.PERSON])

        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {"channel": 0, "name": "Front", "table": {"AI_PEOPLE": "0" * 168, "MD": "1" * 168}},
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Person (AI)" in response.text
        assert "Show all" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_ai_and_md_device_shows_both_in_summary(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        """Device with MOTION + PERSON → summary has both MD and AI_PEOPLE keys."""
        camera = await create_camera(channel=0)
        await set_detection_types(camera.id, [DetectionType.MOTION, DetectionType.PERSON])

        mock_client = AsyncMock()
        mock_client.get_push_schedules.return_value = [
            {
                "channel": 0,
                "name": "Front",
                "table": {"MD": "1" * 168, "AI_PEOPLE": "0" * 168, "AI_VEHICLE": "0" * 168},
            },
        ]
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert "Motion Detection" in response.text
        assert "Person (AI)" in response.text
        assert "Show all" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_schedules_timeout(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.login.side_effect = asyncio.TimeoutError
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert response.status_code == 200
        assert "timed out" in response.text

    @patch("remander.routes.admin.ReolinkNVRClient")
    async def test_query_schedules_error(
        self, mock_nvr_cls: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        mock_client = AsyncMock()
        mock_client.login.side_effect = ConnectionError("Connection refused")
        mock_nvr_cls.return_value = mock_client

        response = await logged_in_client.post("/admin/query-push-schedules")
        assert response.status_code == 200
        assert "Connection refused" in response.text


class TestNvrSyncCreate:
    async def test_creates_device_returns_ok_row(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/admin/nvr-sync/create",
            data={
                "channel": "0",
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": "true",
            },
        )
        assert response.status_code == 200
        assert "OK" in response.text
        device = await Device.get(channel=0)
        assert device.name == "Front"

    async def test_duplicate_name_returns_error_toast(self, logged_in_client: AsyncClient) -> None:
        await create_camera(name="Front", channel=5)
        response = await logged_in_client.post(
            "/admin/nvr-sync/create",
            data={
                "channel": "0",
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": "true",
            },
        )
        assert response.status_code == 200
        assert "already exists" in response.text


class TestNvrSyncUpdate:
    async def test_updates_device_returns_ok_row(self, logged_in_client: AsyncClient) -> None:
        device = await create_camera(name="OldName", channel=0, model_name="RLC-810A")
        response = await logged_in_client.post(
            "/admin/nvr-sync/update",
            data={
                "device_id": str(device.id),
                "channel": "0",
                "name": "NewName",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "2.0",
                "online": "true",
            },
        )
        assert response.status_code == 200
        assert "OK" in response.text
        await device.refresh_from_db()
        assert device.name == "NewName"


class TestNvrSyncAll:
    async def test_bulk_sync_returns_full_table(self, logged_in_client: AsyncClient) -> None:
        cameras_json = json.dumps(
            [
                {
                    "channel": 0,
                    "name": "Front",
                    "model": "RLC-810A",
                    "hw_version": "v1",
                    "firmware": "3.0",
                    "online": True,
                },
                {
                    "channel": 1,
                    "name": "Back",
                    "model": "RLC-520A",
                    "hw_version": "v2",
                    "firmware": "2.0",
                    "online": False,
                },
            ]
        )
        response = await logged_in_client.post(
            "/admin/nvr-sync/sync-all",
            data={"cameras_json": cameras_json},
        )
        assert response.status_code == 200
        # After sync, both devices should be OK
        assert "OK" in response.text
        # Check devices were created
        assert await Device.filter(channel=0).exists()
        assert await Device.filter(channel=1).exists()
