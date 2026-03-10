"""Tests for hot water routes — TDD red/green approach."""

from pathlib import Path
from unittest.mock import MagicMock, patch

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
    async def test_status_when_inactive(self, client) -> None:
        response = await client.get("/hot-water/status")
        assert response.status_code == 286  # HTMX stop polling

    async def test_status_when_active(self, client) -> None:
        from datetime import datetime, timedelta, timezone

        from remander.plugins.data import set_plugin_value

        end_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        await set_plugin_value(
            "hot_water",
            "timer_state",
            {"end_time": end_time.isoformat(), "duration_minutes": 20, "job_id": "j1"},
        )
        response = await client.get("/hot-water/status")
        assert response.status_code == 200
        assert "Cancel" in response.text


class TestHotWaterStart:
    @patch("remander_hot_water.routes.start_hot_water")
    @patch("remander_hot_water.routes.get_queue")
    async def test_start_calls_service(self, mock_get_queue, mock_start, client) -> None:
        mock_get_queue.return_value = MagicMock()
        mock_start.return_value = None

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
    async def test_start_returns_html(self, mock_get_queue, mock_start, client) -> None:
        mock_get_queue.return_value = MagicMock()
        mock_start.return_value = None

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
    async def test_cancel_calls_service(self, mock_get_queue, mock_cancel, client) -> None:
        mock_get_queue.return_value = MagicMock()
        mock_cancel.return_value = None

        response = await client.post(
            "/hot-water/cancel",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        mock_cancel.assert_awaited_once()
        assert response.status_code == 200
