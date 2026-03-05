"""Admin route handlers — NVR query, pending jobs, audit trail."""

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from remander.clients.reolink import ReolinkNVRClient
from remander.services.command import list_commands

logger = logging.getLogger(__name__)

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
    logger.info("Querying NVR at %s:%s", settings.nvr_host, settings.nvr_port)
    client = ReolinkNVRClient(
        host=settings.nvr_host,
        port=settings.nvr_port,
        username=settings.nvr_username,
        password=settings.nvr_password.get_secret_value(),
        timeout=settings.nvr_timeout,
    )

    async def _query() -> list[dict]:
        await client.login()
        channels = await client.list_channels()
        await client.logout()
        return channels

    try:
        cameras = await asyncio.wait_for(_query(), timeout=settings.nvr_timeout)
    except TimeoutError:
        logger.warning("NVR query timed out after %ds", settings.nvr_timeout)
        cameras = []
        error = f"NVR query timed out after {settings.nvr_timeout}s"
        return templates.TemplateResponse(
            request,
            "admin/_nvr_results.html",
            {"cameras": cameras, "error": error},
        )
    except Exception as e:
        logger.warning("NVR query failed: %s", e)
        cameras = []
        error = str(e)
        return templates.TemplateResponse(
            request,
            "admin/_nvr_results.html",
            {"cameras": cameras, "error": error},
        )

    logger.info("NVR query returned %d cameras", len(cameras))
    return templates.TemplateResponse(
        request,
        "admin/_nvr_results.html",
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
