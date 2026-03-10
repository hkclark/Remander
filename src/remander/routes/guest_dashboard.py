"""Guest dashboard route — lightweight public dashboard at /d."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from remander.config import get_settings
from remander.models.state import AppState
from remander.services.dashboard_button import list_dashboard_buttons

router = APIRouter()


@router.get("/d", response_class=HTMLResponse)
async def guest_dashboard(request: Request) -> HTMLResponse:
    from remander.main import templates

    settings = get_settings()

    current_mode: str | None = None
    if settings.guest_dashboard_show_mode:
        mode_record = await AppState.get_or_none(key="current_mode")
        current_mode = mode_record.value if mode_record else "home"

    dashboard_buttons = await list_dashboard_buttons(enabled_only=True, show_on_guest=True)

    return templates.TemplateResponse(
        request,
        "guest_dashboard.html",
        {
            "current_mode": current_mode,
            "dashboard_buttons": dashboard_buttons,
            "show_mode": settings.guest_dashboard_show_mode,
        },
    )
