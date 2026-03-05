"""Admin route handlers — NVR query, pending jobs, audit trail."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from remander.clients.reolink import ReolinkNVRClient
from remander.services.command import list_commands

router = APIRouter(prefix="/admin")


@router.get("", response_class=HTMLResponse)
async def admin_index(request: Request) -> HTMLResponse:
    from remander.main import templates

    return templates.TemplateResponse(request, "admin/index.html", {})


@router.post("/query-nvr", response_class=HTMLResponse)
async def query_nvr(request: Request) -> HTMLResponse:
    from remander.config import get_settings
    from remander.main import templates

    settings = get_settings()
    client = ReolinkNVRClient(
        host=settings.nvr_host,
        port=settings.nvr_port,
        username=settings.nvr_username,
        password=settings.nvr_password.get_secret_value(),
    )

    try:
        await client.login()
        cameras = await client.list_channels()
        await client.logout()
    except Exception as e:
        cameras = []
        error = str(e)
        return templates.TemplateResponse(
            request,
            "admin/nvr_cameras.html",
            {"cameras": cameras, "error": error},
        )

    return templates.TemplateResponse(
        request,
        "admin/nvr_cameras.html",
        {"cameras": cameras, "error": None},
    )


@router.get("/pending-jobs", response_class=HTMLResponse)
async def pending_jobs(request: Request) -> HTMLResponse:
    from remander.main import templates
    from remander.models.command import Command
    from remander.models.enums import CommandStatus

    pending = await Command.filter(
        status__in=[CommandStatus.PENDING, CommandStatus.QUEUED]
    ).order_by("created_at")

    return templates.TemplateResponse(
        request,
        "admin/pending_jobs.html",
        {"pending_commands": pending},
    )


@router.get("/audit", response_class=HTMLResponse)
async def audit_trail(request: Request) -> HTMLResponse:
    from remander.main import templates

    commands = await list_commands(limit=100)
    return templates.TemplateResponse(
        request,
        "admin/audit.html",
        {"commands": commands},
    )
