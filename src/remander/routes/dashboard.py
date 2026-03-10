"""Dashboard route handlers."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from remander.config import get_settings
from remander.models.state import AppState
from remander.plugins.registry import get_registry
from remander.services.command import get_active_command, list_commands
from remander.services.dashboard_button import list_dashboard_buttons
from remander.services.tag import list_dashboard_tags

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    from remander.main import templates

    mode_record = await AppState.get_or_none(key="current_mode")
    current_mode = mode_record.value if mode_record else "home"

    commands = await list_commands(limit=1)
    last_command = commands[0] if commands else None

    active_command = await get_active_command()
    dashboard_tags = await list_dashboard_tags()
    dashboard_buttons = await list_dashboard_buttons(enabled_only=True, show_on_main=True)
    settings = get_settings()
    plugin_widgets = get_registry().all_dashboard_widgets("dashboard")

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current_mode": current_mode,
            "last_command": last_command,
            "active_command": active_command,
            "dashboard_tags": dashboard_tags,
            "dashboard_buttons": dashboard_buttons,
            "debug": settings.debug,
            "plugin_widgets": plugin_widgets,
        },
    )


@router.get("/partials/command-progress", response_class=HTMLResponse)
async def command_progress(request: Request) -> HTMLResponse:
    from remander.main import templates

    active_command = await get_active_command()
    # HTMX treats 286 as "stop polling" — stop once the command finishes
    status_code = 200 if active_command else 286
    return templates.TemplateResponse(
        request,
        "partials/command_progress.html",
        {"active_command": active_command},
        status_code=status_code,
    )
