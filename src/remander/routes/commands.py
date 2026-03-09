"""Command route handlers — execution, history, detail, cancellation."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from remander.models.device import Device
from remander.models.enums import CommandType, Mode
from remander.services.bitmask import find_devices_missing_bitmasks
from remander.services.command import (
    cancel_command,
    create_command,
    get_command,
    list_commands,
)
from remander.services.queue import enqueue_command
from remander.services.tag import get_devices_by_tag, list_tags

router = APIRouter(prefix="/commands")


async def _bitmask_error_response(
    request: Request,
    tag_filter: str | None,
    mode: Mode,
) -> HTMLResponse | None:
    """Return an error response if any camera devices are missing bitmask assignments.

    Returns None when validation passes (command can proceed).
    """
    from remander.main import templates

    if tag_filter:
        devices: list[Device] = []
        for tag_name in tag_filter.split(","):
            devices.extend(await get_devices_by_tag(tag_name.strip()))
        device_ids = [d.id for d in devices if d.is_enabled]
    else:
        all_devices = await Device.filter(is_enabled=True)
        device_ids = [d.id for d in all_devices]

    missing = await find_devices_missing_bitmasks(device_ids, mode)
    if not missing:
        return None

    return templates.TemplateResponse(
        request,
        "commands/error.html",
        {"problem_devices": missing, "mode": mode},
        status_code=422,
    )


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
async def execute_set_away_now(request: Request, user: str | None = None) -> Response:
    if error := await _bitmask_error_response(request, tag_filter=None, mode=Mode.AWAY):
        return error
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
) -> Response:
    if error := await _bitmask_error_response(request, tag_filter=None, mode=Mode.AWAY):
        return error
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
) -> Response:
    if error := await _bitmask_error_response(request, tag_filter=tag_filter, mode=Mode.AWAY):
        return error
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
) -> Response:
    if error := await _bitmask_error_response(request, tag_filter=tag_filter, mode=Mode.AWAY):
        return error
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
