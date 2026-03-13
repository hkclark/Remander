"""Guest dashboard route — lightweight public dashboard at /d."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from remander.config import get_settings
from remander.models.enums import ButtonOperationType, CommandType
from remander.models.state import AppState
from remander.plugins.registry import get_registry
from remander.services.command import create_command
from remander.services.dashboard_button import get_dashboard_button, list_dashboard_buttons
from remander.services.queue import enqueue_command

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
    pin_error = request.query_params.get("pin_error") == "1"
    show_toast = request.query_params.get("submitted") == "1"
    plugin_widgets = get_registry().all_dashboard_widgets("guest_dashboard")

    return templates.TemplateResponse(
        request,
        "guest_dashboard.html",
        {
            "current_mode": current_mode,
            "dashboard_buttons": dashboard_buttons,
            "show_mode": settings.guest_dashboard_show_mode,
            "pin_error": pin_error,
            "show_toast": show_toast,
            "plugin_widgets": plugin_widgets,
        },
    )


@router.post("/d/execute/button/{button_id}")
async def guest_execute_button(
    request: Request,
    button_id: int,
    pin: str = Form(""),
) -> Response:
    button = await get_dashboard_button(button_id)
    if button is None or not button.show_on_guest or not button.is_enabled:
        return HTMLResponse("Button not found", status_code=404)

    if button.operation_type == ButtonOperationType.HOME:
        settings = get_settings()
        if pin != settings.guest_dashboard_pin:
            return RedirectResponse(url="/d?pin_error=1", status_code=303)

    match button.operation_type:
        case ButtonOperationType.AWAY:
            command_type = CommandType.SET_AWAY_NOW
        case ButtonOperationType.HOME:
            command_type = CommandType.SET_HOME_NOW
        case ButtonOperationType.OTHER:
            command_type = CommandType.APPLY_BITMASK

    cmd = await create_command(
        command_type,
        delay_seconds=button.delay_seconds if button.delay_seconds else None,
        dashboard_button_id=button.id,
        initiated_by_ip=request.client.host if request.client else None,
    )
    await enqueue_command(cmd.id)
    return RedirectResponse(url="/d?submitted=1", status_code=303)
