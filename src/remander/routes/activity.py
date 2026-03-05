"""Activity log route handlers."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from remander.models.activity import ActivityLog
from remander.models.enums import ActivityStatus

router = APIRouter(prefix="/activity")


@router.get("", response_class=HTMLResponse)
async def activity_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    qs = ActivityLog.all().order_by("-created_at")

    command_id = request.query_params.get("command_id")
    device_id = request.query_params.get("device_id")
    status = request.query_params.get("status")

    if command_id:
        qs = qs.filter(command_id=int(command_id))
    if device_id:
        qs = qs.filter(device_id=int(device_id))
    if status:
        qs = qs.filter(status=ActivityStatus(status))

    activities = await qs.limit(100)

    return templates.TemplateResponse(
        request,
        "activity/list.html",
        {
            "activities": activities,
            "filters": {
                "command_id": command_id or "",
                "device_id": device_id or "",
                "status": status or "",
            },
        },
    )
