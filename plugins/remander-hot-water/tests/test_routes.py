"""Tests for hot water routes — TDD red/green approach."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jinja2 import ChoiceLoader, FileSystemLoader
from remander_hot_water.routes import router

PLUGIN_TEMPLATE_DIR = str(
    Path(__file__).resolve().parent.parent / "src" / "remander_hot_water" / "templates"
)


@pytest.fixture(autouse=True)
def _setup_templates():
    """Configure Jinja2 templates to include plugin template directory."""
    import remander.main as main_module

    original_loader = main_module.templates.env.loader
    main_module.templates.env.loader = ChoiceLoader(
        [FileSystemLoader("src/remander/templates"), FileSystemLoader(PLUGIN_TEMPLATE_DIR)]
    )
    yield
    main_module.templates.env.loader = original_loader


@pytest.fixture
def app():
    """Create a minimal FastAPI app with hot water routes for testing."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHotWaterStatus:
    @patch("remander_hot_water.routes.get_status")
    async def test_status_when_idle_returns_286(self, mock_get_status, client) -> None:
        mock_get_status.return_value = {"active": False, "device_state": "off"}
        response = await client.get("/hot-water/status")
        assert response.status_code == 286

    @patch("remander_hot_water.routes.get_status")
    async def test_status_when_active_returns_200(self, mock_get_status, client) -> None:
        mock_get_status.return_value = {
            "active": True,
            "device_state": "on",
            "remaining_seconds": 600,
            "duration_minutes": 20,
            "end_time": "2026-03-10T20:00:00+00:00",
        }
        response = await client.get("/hot-water/status")
        assert response.status_code == 200
        assert "Cancel" in response.text

    @patch("remander_hot_water.routes.get_status")
    async def test_status_when_unreachable_returns_200(self, mock_get_status, client) -> None:
        """Unreachable keeps polling so the UI self-recovers when device comes back."""
        mock_get_status.return_value = {"active": False, "device_state": "unreachable"}
        response = await client.get("/hot-water/status")
        assert response.status_code == 200

    @patch("remander_hot_water.routes.get_status")
    async def test_status_when_external_returns_200(self, mock_get_status, client) -> None:
        """Device on but no timer — external start — keeps polling."""
        mock_get_status.return_value = {"active": False, "device_state": "on"}
        response = await client.get("/hot-water/status")
        assert response.status_code == 200


class TestHotWaterStart:
    @patch("remander_hot_water.routes.start_hot_water")
    @patch("remander_hot_water.routes.get_queue")
    @patch("remander_hot_water.routes.get_status")
    async def test_start_calls_service(
        self, mock_get_status, mock_get_queue, mock_start, client
    ) -> None:
        mock_get_queue.return_value = MagicMock()
        mock_start.return_value = None
        mock_get_status.return_value = {"active": True, "device_state": "on",
                                        "remaining_seconds": 1200, "duration_minutes": 20,
                                        "end_time": "2026-03-10T20:00:00+00:00"}

        await client.post(
            "/hot-water/start",
            data={"duration_minutes": "20"},
            follow_redirects=False,
        )
        mock_start.assert_awaited_once()
        call_kwargs = mock_start.call_args[1]
        assert call_kwargs["duration_minutes"] == 20

    @patch("remander_hot_water.routes.start_hot_water")
    @patch("remander_hot_water.routes.get_queue")
    @patch("remander_hot_water.routes.get_status")
    async def test_start_returns_html(
        self, mock_get_status, mock_get_queue, mock_start, client
    ) -> None:
        mock_get_queue.return_value = MagicMock()
        mock_start.return_value = None
        mock_get_status.return_value = {"active": True, "device_state": "on",
                                        "remaining_seconds": 1200, "duration_minutes": 20,
                                        "end_time": "2026-03-10T20:00:00+00:00"}

        response = await client.post(
            "/hot-water/start",
            data={"duration_minutes": "20"},
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 200


class TestHotWaterCancel:
    @patch("remander_hot_water.routes.cancel_hot_water")
    @patch("remander_hot_water.routes.get_queue")
    @patch("remander_hot_water.routes.get_status")
    async def test_cancel_calls_service(
        self, mock_get_status, mock_get_queue, mock_cancel, client
    ) -> None:
        mock_get_queue.return_value = MagicMock()
        mock_cancel.return_value = None
        mock_get_status.return_value = {"active": False, "device_state": "off"}

        response = await client.post(
            "/hot-water/cancel",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        mock_cancel.assert_awaited_once()
        assert response.status_code == 200
