"""Hot water plugin routes — start, cancel, and status endpoints."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from remander.clients.sonoff import SonoffClient
from remander.worker import get_queue
from remander_hot_water.service import cancel_hot_water, get_status, start_hot_water
from remander_hot_water.settings import HotWaterSettings

router = APIRouter(prefix="/hot-water", tags=["hot-water"])


@router.get("/status", response_class=HTMLResponse)
async def hot_water_status(request: Request) -> HTMLResponse:
    """Return the current status partial (polled by HTMX)."""
    from remander.main import templates

    status = await get_status()
    settings = HotWaterSettings()

    if not status["active"]:
        # 286 tells HTMX to stop polling
        return templates.TemplateResponse(
            request,
            "hot_water/_status_partial.html",
            {"status": status, "settings": settings},
            status_code=286,
        )

    return templates.TemplateResponse(
        request,
        "hot_water/_status_partial.html",
        {"status": status, "settings": settings},
    )


@router.post("/start", response_class=HTMLResponse)
async def hot_water_start(
    request: Request,
    duration_minutes: int = Form(...),
) -> HTMLResponse:
    """Start the hot water pump for the specified duration."""
    from remander.main import templates

    settings = HotWaterSettings()
    queue = get_queue()
    sonoff = SonoffClient()

    await start_hot_water(
        settings=settings,
        sonoff_client=sonoff,
        queue=queue,
        duration_minutes=duration_minutes,
    )

    status = await get_status()
    return templates.TemplateResponse(
        request,
        "hot_water/_status_partial.html",
        {"status": status, "settings": settings},
    )


@router.post("/cancel", response_class=HTMLResponse)
async def hot_water_cancel(request: Request) -> HTMLResponse:
    """Cancel the hot water timer and turn off the pump."""
    from remander.main import templates

    settings = HotWaterSettings()
    queue = get_queue()
    sonoff = SonoffClient()

    await cancel_hot_water(
        settings=settings,
        sonoff_client=sonoff,
        queue=queue,
    )

    status = await get_status()
    return templates.TemplateResponse(
        request,
        "hot_water/_status_partial.html",
        {"status": status, "settings": settings},
    )
