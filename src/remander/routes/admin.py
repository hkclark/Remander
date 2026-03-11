"""Admin route handlers — NVR query, pending jobs, audit trail, NVR sync, settings."""

import asyncio
import json
import logging
from typing import Any

import attrs
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


# ── Settings group definitions ────────────────────────────────────────────────


@attrs.define
class SettingsField:
    """Metadata for a single field in the settings admin UI."""

    key: str
    label: str
    field_type: str = "string"  # "string" | "int" | "bool" | "float" | "password"
    secret: bool = False
    restart_required: bool = False


@attrs.define
class SettingsGroup:
    """A labelled group of settings fields shown as one save-able section."""

    id: str
    title: str
    fields: list[SettingsField]


# Core settings groups — mirrors remander.config.Settings fields
CORE_SETTINGS_GROUPS: list[SettingsGroup] = [
    SettingsGroup(
        id="nvr",
        title="NVR",
        fields=[
            SettingsField("nvr_host", "Host"),
            SettingsField("nvr_port", "Port", field_type="int"),
            SettingsField("nvr_username", "Username"),
            SettingsField("nvr_password", "Password", field_type="password", secret=True),
            SettingsField("nvr_use_https", "Use HTTPS", field_type="bool"),
            SettingsField("nvr_timeout", "Timeout (seconds)", field_type="int"),
        ],
    ),
    SettingsGroup(
        id="email",
        title="Email Notifications",
        fields=[
            SettingsField("smtp_host", "SMTP Host"),
            SettingsField("smtp_port", "SMTP Port", field_type="int"),
            SettingsField("smtp_username", "Username"),
            SettingsField(
                "smtp_password", "Password", field_type="password", secret=True
            ),
            SettingsField("smtp_from", "From Address"),
            SettingsField("smtp_to", "To Address"),
            SettingsField("smtp_use_tls", "Use TLS", field_type="bool"),
        ],
    ),
    SettingsGroup(
        id="location",
        title="Location",
        fields=[
            SettingsField("latitude", "Latitude", field_type="float"),
            SettingsField("longitude", "Longitude", field_type="float"),
        ],
    ),
    SettingsGroup(
        id="guest_dashboard",
        title="Guest Dashboard",
        fields=[
            SettingsField(
                "guest_dashboard_show_mode", "Show current mode", field_type="bool"
            ),
            SettingsField("guest_dashboard_pin", "PIN", field_type="password", secret=True),
        ],
    ),
    SettingsGroup(
        id="advanced",
        title="Advanced",
        fields=[
            SettingsField("debug", "Debug mode", field_type="bool"),
            SettingsField(
                "log_level", "Log level", restart_required=True
            ),
            SettingsField(
                "power_on_timeout_seconds", "Power-on timeout (s)", field_type="int"
            ),
            SettingsField(
                "power_on_poll_interval_seconds",
                "Power-on poll interval (s)",
                field_type="int",
            ),
            SettingsField("job_timeout_seconds", "Job timeout (s)", field_type="int"),
        ],
    ),
]

# Settings that stay in .env (shown read-only)
READ_ONLY_SETTINGS = [
    "database_url",
    "redis_url",
    "puid",
    "pgid",
    "nvr_debug",
    "nvr_debug_max_length",
    "workflow_debug",
    "session_secret_key",
    "password_reset_expiry_seconds",
    "invitation_expiry_seconds",
]

_GROUP_BY_ID = {g.id: g for g in CORE_SETTINGS_GROUPS}


def _coerce_value(raw: str, field_type: str) -> Any:
    """Coerce a form string value to the appropriate Python type."""
    if field_type == "int":
        return int(raw)
    if field_type == "float":
        return float(raw)
    if field_type == "bool":
        return raw.lower() in ("true", "1", "on", "yes")
    return raw  # string / password


@router.get("", response_class=HTMLResponse)
async def admin_index(request: Request) -> HTMLResponse:
    from remander.auth import get_current_user_optional
    from remander.main import templates

    current_user = await get_current_user_optional(request)
    return templates.TemplateResponse(request, "admin/index.html", {"current_user": current_user})


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request) -> HTMLResponse:
    """Settings page — shows all configurable fields grouped by section."""
    from remander.auth import get_current_user_optional
    from remander.config import get_settings
    from remander.main import templates
    from remander.plugins.registry import get_registry
    from remander.services.app_config import get_all_config

    current_user = await get_current_user_optional(request)

    settings = get_settings()
    settings_dict = settings.model_dump()

    # Read DB-stored overrides directly — this is the ground truth for what the
    # user has saved, independent of the in-memory cache.
    db_values = await get_all_config(prefix=None)
    db_plugin_values = await get_all_config(prefix="plugin.")

    def _field_value(key: str, default: Any = "") -> Any:
        """DB value if set, otherwise fall back to the current in-memory setting."""
        if key in db_values:
            return db_values[key]
        return settings_dict.get(key, default)

    # Build current values for each group (secrets shown blank)
    groups_with_values = []
    for group in CORE_SETTINGS_GROUPS:
        field_values = {}
        for f in group.fields:
            field_values[f.key] = "" if f.secret else _field_value(f.key)
        groups_with_values.append({"group": group, "current_values": field_values})

    # Read-only values come from the live settings (always .env-sourced)
    read_only_values = {k: settings_dict.get(k, "") for k in READ_ONLY_SETTINGS}

    # Plugin sections — read directly from DB plugin values, fall back to field default
    registry = get_registry()
    plugin_sections = []
    for plugin_name, fields in registry.all_settings_fields().items():
        field_values = {}
        for f in fields:
            if f.secret:
                field_values[f.key] = ""
            else:
                db_key = f"plugin.{plugin_name}.{f.key}"
                field_values[f.key] = (
                    db_plugin_values[db_key] if db_key in db_plugin_values else f.default
                )
        plugin_sections.append(
            {"plugin_name": plugin_name, "fields": fields, "current_values": field_values}
        )

    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {
            "groups_with_values": groups_with_values,
            "read_only_values": read_only_values,
            "plugin_sections": plugin_sections,
            "current_user": current_user,
        },
    )


@router.post("/settings/core/{group_id}", response_class=HTMLResponse)
async def save_core_settings(
    request: Request,
    group_id: str,
) -> HTMLResponse:
    """Save a core settings group. Returns HTMX-compatible toast partial."""
    from fastapi import HTTPException

    from remander.main import templates
    from remander.services.app_config import get_config_value, load_core_config, set_config_value

    group = _GROUP_BY_ID.get(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Unknown settings group: {group_id}")

    form_data = await request.form()

    for field in group.fields:
        raw = form_data.get(field.key, "")

        if field.secret and not raw:
            # Empty secret field — do not overwrite stored value
            continue

        try:
            value = _coerce_value(str(raw), field.field_type)
        except (ValueError, TypeError):
            logger.warning("Invalid value for %s: %r — skipping", field.key, raw)
            continue

        await set_config_value(field.key, value)

    await load_core_config()

    return templates.TemplateResponse(
        request,
        "admin/_settings_toast.html",
        {"message": f"{group.title} settings saved", "level": "success"},
    )


@router.post("/settings/plugin/{plugin_name}", response_class=HTMLResponse)
async def save_plugin_settings(
    request: Request,
    plugin_name: str,
) -> HTMLResponse:
    """Save settings for a plugin. Returns HTMX-compatible toast partial."""
    from fastapi import HTTPException

    from remander.main import templates
    from remander.plugins.registry import get_registry
    from remander.services.app_config import set_plugin_setting

    registry = get_registry()
    plugin = registry.get(plugin_name)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Unknown plugin: {plugin_name}")

    fields = plugin.settings_fields()
    form_data = await request.form()

    for field in fields:
        raw = str(form_data.get(field.key, ""))

        if field.secret and not raw:
            continue

        if field.field_type == "int":
            try:
                value: Any = int(raw)
            except (ValueError, TypeError):
                continue
        elif field.field_type == "float":
            try:
                value = float(raw)
            except (ValueError, TypeError):
                continue
        elif field.field_type == "bool":
            value = raw.lower() in ("true", "1", "on", "yes")
        elif field.field_type == "list_int":
            try:
                value = [int(x.strip()) for x in raw.split(",") if x.strip()]
            except ValueError:
                continue
        else:
            value = raw

        await set_plugin_setting(plugin_name, field.key, value)

    return templates.TemplateResponse(
        request,
        "admin/_settings_toast.html",
        {"message": f"{plugin_name.replace('_', ' ').title()} settings saved", "level": "success"},
    )


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
