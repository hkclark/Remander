"""Admin route handlers — NVR query, pending jobs, audit trail, NVR sync."""

import asyncio
import json
import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from tortoise.exceptions import IntegrityError

from remander.clients.reolink import ReolinkNVRClient
from remander.models.device import Device
from remander.models.enums import DeviceBrand, DeviceType
from remander.services.command import list_commands
from remander.services.nvr_sync import (
    ChannelSyncResult,
    compare_channels,
    create_device_from_channel,
    sync_all_channels,
    update_device_from_channel,
)

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
        use_https=settings.nvr_use_https,
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
        return templates.TemplateResponse(
            request,
            "admin/_nvr_results.html",
            {
                "sync_results": [],
                "cameras_json": "[]",
                "has_actionable": False,
                "error": f"NVR query timed out after {settings.nvr_timeout}s",
            },
        )
    except Exception as e:
        logger.warning("NVR query failed: %s", e)
        return templates.TemplateResponse(
            request,
            "admin/_nvr_results.html",
            {"sync_results": [], "cameras_json": "[]", "has_actionable": False, "error": str(e)},
        )

    logger.info("NVR query returned %d cameras", len(cameras))

    # Compare against existing Reolink camera devices
    existing_devices = await Device.filter(device_type=DeviceType.CAMERA, brand=DeviceBrand.REOLINK)
    sync_results = compare_channels(cameras, existing_devices)
    has_actionable = any(r.status != "ok" for r in sync_results)

    return templates.TemplateResponse(
        request,
        "admin/_nvr_results.html",
        {
            "sync_results": sync_results,
            "cameras_json": json.dumps(cameras),
            "has_actionable": has_actionable,
            "error": None,
        },
    )


@router.post("/query-push-schedules", response_class=HTMLResponse)
async def query_push_schedules(request: Request) -> HTMLResponse:
    from remander.config import get_settings
    from remander.main import templates

    settings = get_settings()
    client = ReolinkNVRClient(
        host=settings.nvr_host,
        port=settings.nvr_port,
        username=settings.nvr_username,
        password=settings.nvr_password.get_secret_value(),
        use_https=settings.nvr_use_https,
        timeout=settings.nvr_timeout,
    )

    async def _query() -> list[dict]:
        await client.login()
        schedules = await client.get_push_schedules()
        await client.logout()
        return schedules

    try:
        schedules = await asyncio.wait_for(_query(), timeout=settings.nvr_timeout)
    except TimeoutError:
        logger.warning("Push schedule query timed out after %ds", settings.nvr_timeout)
        return templates.TemplateResponse(
            request,
            "admin/_push_schedules.html",
            {"schedules": [], "error": f"NVR query timed out after {settings.nvr_timeout}s"},
        )
    except Exception as e:
        logger.warning("Push schedule query failed: %s", e)
        return templates.TemplateResponse(
            request,
            "admin/_push_schedules.html",
            {"schedules": [], "error": str(e)},
        )

    logger.info("Push schedule query returned %d channels", len(schedules))
    return templates.TemplateResponse(
        request,
        "admin/_push_schedules.html",
        {"schedules": schedules, "error": None},
    )


@router.post("/nvr-sync/create", response_class=HTMLResponse)
async def nvr_sync_create(
    request: Request,
    channel: int = Form(),
    name: str = Form(),
    model: str = Form(""),
    hw_version: str = Form(""),
    firmware: str = Form(""),
    online: str = Form("false"),
) -> HTMLResponse:
    from remander.main import templates

    channel_data = {
        "channel": channel,
        "name": name,
        "model": model or None,
        "hw_version": hw_version or None,
        "firmware": firmware or None,
    }

    try:
        device = await create_device_from_channel(channel_data)
    except IntegrityError:
        # Duplicate device name
        result = ChannelSyncResult(
            channel=channel,
            name=name,
            model=model or None,
            hw_version=hw_version or None,
            firmware=firmware or None,
            online=online.lower() == "true",
            status="new",
            device_id=None,
        )
        return templates.TemplateResponse(
            request,
            "admin/_nvr_sync_row.html",
            {
                "result": result,
                "toast_message": f'Device "{name}" already exists',
                "toast_level": "error",
            },
        )

    result = ChannelSyncResult(
        channel=channel,
        name=name,
        model=model or None,
        hw_version=hw_version or None,
        firmware=firmware or None,
        online=online.lower() == "true",
        status="ok",
        device_id=device.id,
    )
    return templates.TemplateResponse(
        request,
        "admin/_nvr_sync_row.html",
        {
            "result": result,
            "toast_message": f'Created device "{name}"',
            "toast_level": "success",
        },
    )


@router.post("/nvr-sync/update", response_class=HTMLResponse)
async def nvr_sync_update(
    request: Request,
    device_id: int = Form(),
    channel: int = Form(),
    name: str = Form(),
    model: str = Form(""),
    hw_version: str = Form(""),
    firmware: str = Form(""),
    online: str = Form("false"),
) -> HTMLResponse:
    from remander.main import templates

    channel_data = {
        "channel": channel,
        "name": name,
        "model": model or None,
        "hw_version": hw_version or None,
        "firmware": firmware or None,
    }

    await update_device_from_channel(device_id, channel_data)

    result = ChannelSyncResult(
        channel=channel,
        name=name,
        model=model or None,
        hw_version=hw_version or None,
        firmware=firmware or None,
        online=online.lower() == "true",
        status="ok",
        device_id=device_id,
    )
    return templates.TemplateResponse(
        request,
        "admin/_nvr_sync_row.html",
        {
            "result": result,
            "toast_message": f'Updated device "{name}"',
            "toast_level": "success",
        },
    )


@router.post("/nvr-sync/sync-all", response_class=HTMLResponse)
async def nvr_sync_all(
    request: Request,
    cameras_json: str = Form(),
) -> HTMLResponse:
    from remander.main import templates

    cameras = json.loads(cameras_json)
    existing_devices = await Device.filter(device_type=DeviceType.CAMERA, brand=DeviceBrand.REOLINK)

    created, updated = await sync_all_channels(cameras, existing_devices)

    # Re-fetch devices and re-compare to get up-to-date sync results
    refreshed_devices = await Device.filter(
        device_type=DeviceType.CAMERA, brand=DeviceBrand.REOLINK
    )
    sync_results = compare_channels(cameras, refreshed_devices)
    has_actionable = any(r.status != "ok" for r in sync_results)

    return templates.TemplateResponse(
        request,
        "admin/_nvr_results.html",
        {
            "sync_results": sync_results,
            "cameras_json": cameras_json,
            "has_actionable": has_actionable,
            "error": None,
            "toast_message": f"Synced: {created} created, {updated} updated",
            "toast_level": "success",
        },
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
