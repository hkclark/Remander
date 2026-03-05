"""Dashboard route handlers."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from remander.models.state import AppState
from remander.services.command import get_active_command, list_commands

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    from remander.main import templates

    mode_record = await AppState.get_or_none(key="current_mode")
    current_mode = mode_record.value if mode_record else "home"

    commands = await list_commands(limit=1)
    last_command = commands[0] if commands else None

    active_command = await get_active_command()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current_mode": current_mode,
            "last_command": last_command,
            "active_command": active_command,
        },
    )


@router.get("/partials/command-progress", response_class=HTMLResponse)
async def command_progress(request: Request) -> HTMLResponse:
    from remander.main import templates

    active_command = await get_active_command()
    return templates.TemplateResponse(
        request,
        "partials/command_progress.html",
        {"active_command": active_command},
    )
