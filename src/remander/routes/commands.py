"""Command route handlers — execution, history, detail, cancellation."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.models.enums import CommandType
from remander.services.command import (
    cancel_command,
    create_command,
    get_command,
    list_commands,
)
from remander.services.queue import enqueue_command
from remander.services.tag import list_tags

router = APIRouter(prefix="/commands")


@router.get("/execute", response_class=HTMLResponse)
async def command_execute_page(request: Request) -> HTMLResponse:
    from remander.main import templates

    tags = await list_tags()
    return templates.TemplateResponse(
        request,
        "commands/execute.html",
        {"tags": tags},
    )


@router.post("/execute/set-away-now")
async def execute_set_away_now(request: Request, user: str | None = None) -> RedirectResponse:
    cmd = await create_command(
        CommandType.SET_AWAY_NOW,
        initiated_by_ip=request.client.host if request.client else None,
        initiated_by_user=request.query_params.get("user"),
    )
    await enqueue_command(cmd.id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/execute/set-away-delayed")
async def execute_set_away_delayed(
    request: Request,
    delay_minutes: str = Form(...),
) -> RedirectResponse:
    cmd = await create_command(
        CommandType.SET_AWAY_DELAYED,
        delay_minutes=int(delay_minutes),
        initiated_by_ip=request.client.host if request.client else None,
        initiated_by_user=request.query_params.get("user"),
    )
    await enqueue_command(cmd.id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/execute/set-home-now")
async def execute_set_home_now(request: Request) -> RedirectResponse:
    cmd = await create_command(
        CommandType.SET_HOME_NOW,
        initiated_by_ip=request.client.host if request.client else None,
        initiated_by_user=request.query_params.get("user"),
    )
    await enqueue_command(cmd.id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/execute/pause-notifications")
async def execute_pause_notifications(
    request: Request,
    pause_minutes: str = Form(...),
    tag_filter: str | None = Form(None),
) -> RedirectResponse:
    cmd = await create_command(
        CommandType.PAUSE_NOTIFICATIONS,
        pause_minutes=int(pause_minutes),
        tag_filter=tag_filter if tag_filter else None,
        initiated_by_ip=request.client.host if request.client else None,
        initiated_by_user=request.query_params.get("user"),
    )
    await enqueue_command(cmd.id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/execute/pause-recording")
async def execute_pause_recording(
    request: Request,
    pause_minutes: str = Form(...),
    tag_filter: str | None = Form(None),
) -> RedirectResponse:
    cmd = await create_command(
        CommandType.PAUSE_RECORDING,
        pause_minutes=int(pause_minutes),
        tag_filter=tag_filter if tag_filter else None,
        initiated_by_ip=request.client.host if request.client else None,
        initiated_by_user=request.query_params.get("user"),
    )
    await enqueue_command(cmd.id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/{command_id}/cancel")
async def command_cancel(request: Request, command_id: int) -> RedirectResponse:
    await cancel_command(command_id)
    return RedirectResponse(url="/commands", status_code=303)


# --- History & Detail ---


@router.get("", response_class=HTMLResponse)
async def command_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    page = int(request.query_params.get("page", "1"))
    page_size = 20
    commands = await list_commands(limit=page_size * page)
    # Simple pagination: slice to current page
    start = (page - 1) * page_size
    page_commands = commands[start : start + page_size]
    has_next = len(commands) > page * page_size

    return templates.TemplateResponse(
        request,
        "commands/list.html",
        {
            "commands": page_commands,
            "page": page,
            "has_next": has_next,
        },
    )


@router.get("/{command_id}", response_class=HTMLResponse)
async def command_detail(request: Request, command_id: int) -> HTMLResponse:
    from remander.main import templates

    cmd = await get_command(command_id)
    if cmd is None:
        return HTMLResponse("Command not found", status_code=404)

    from remander.services.activity import get_activities_for_command

    activities = await get_activities_for_command(command_id)

    return templates.TemplateResponse(
        request,
        "commands/detail.html",
        {"command": cmd, "activities": activities},
    )
