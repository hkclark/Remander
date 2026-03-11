"""Hot water plugin routes — start, cancel, and status endpoints."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from remander.clients.sonoff import SonoffClient
from remander.services.app_config import get_plugin_setting
from remander.worker import get_queue
from remander_hot_water.service import cancel_hot_water, get_status, start_hot_water
from remander_hot_water.settings import HotWaterSettings

router = APIRouter(prefix="/hot-water", tags=["hot-water"])

PLUGIN_NAME = "hot_water"


def _get_settings() -> HotWaterSettings:
    """Build HotWaterSettings from the plugin config cache (DB-backed, env fallback)."""
    return HotWaterSettings(
        sonoff_ip=get_plugin_setting(PLUGIN_NAME, "sonoff_ip", default="192.168.1.50"),
        default_duration_minutes=get_plugin_setting(
            PLUGIN_NAME, "default_duration_minutes", default=20
        ),
        available_durations=get_plugin_setting(
            PLUGIN_NAME, "available_durations", default=[15, 20, 30]
        ),
    )


@router.get("/status", response_class=HTMLResponse)
async def hot_water_status(request: Request) -> HTMLResponse:
    """Return the current status partial (polled by HTMX)."""
    from remander.main import templates

    settings = _get_settings()
    sonoff = SonoffClient()
    status = await get_status(settings=settings, sonoff_client=sonoff)

    # Only stop polling when the device is cleanly off with no timer.
    # Keep polling for unreachable/error/external so the UI self-recovers.
    idle = not status["active"] and status["device_state"] == "off"

    return templates.TemplateResponse(
        request,
        "hot_water/_status_partial.html",
        {"status": status, "settings": settings},
        status_code=286 if idle else 200,
    )


@router.post("/start", response_class=HTMLResponse)
async def hot_water_start(
    request: Request,
    duration_minutes: int = Form(...),
) -> HTMLResponse:
    """Start the hot water pump for the specified duration."""
    from remander.main import templates

    settings = _get_settings()
    queue = get_queue()
    sonoff = SonoffClient()

    await start_hot_water(
        settings=settings,
        sonoff_client=sonoff,
        queue=queue,
        duration_minutes=duration_minutes,
    )

    status = await get_status(settings=settings, sonoff_client=sonoff)
    return templates.TemplateResponse(
        request,
        "hot_water/_status_partial.html",
        {"status": status, "settings": settings},
    )


@router.post("/cancel", response_class=HTMLResponse)
async def hot_water_cancel(request: Request) -> HTMLResponse:
    """Cancel the hot water timer and turn off the pump."""
    from remander.main import templates

    settings = _get_settings()
    queue = get_queue()
    sonoff = SonoffClient()

    await cancel_hot_water(
        settings=settings,
        sonoff_client=sonoff,
        queue=queue,
    )

    status = await get_status(settings=settings, sonoff_client=sonoff)
    return templates.TemplateResponse(
        request,
        "hot_water/_status_partial.html",
        {"status": status, "settings": settings},
    )
