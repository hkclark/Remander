"""Device route handlers — list, detail, create, edit, delete."""

import asyncio

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.clients.reolink import ReolinkNVRClient
from remander.clients.sonoff import SonoffClient
from remander.clients.tapo import TapoClient
from remander.models.enums import DetectionType, DeviceBrand, DeviceType
from remander.services.detection import get_enabled_detection_types, set_detection_types
from remander.services.device import (
    create_device,
    delete_device,
    get_device,
    list_devices,
    set_power_device,
    update_device,
)
from remander.services.tag import list_tags

router = APIRouter(prefix="/devices")


@router.get("", response_class=HTMLResponse)
async def device_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    devices = await list_devices(prefetch=["tags"], sorted_for_display=True)
    return templates.TemplateResponse(
        request,
        "devices/list.html",
        {"devices": devices},
    )


@router.get("/create", response_class=HTMLResponse)
async def device_create_form(request: Request) -> HTMLResponse:
    from remander.main import templates

    return templates.TemplateResponse(
        request,
        "devices/form.html",
        {
            "device": None,
            "device_types": list(DeviceType),
            "brands": list(DeviceBrand),
        },
    )


@router.post("/create")
async def device_create(
    request: Request,
    name: str = Form(...),
    device_type: str = Form(...),
    brand: str = Form(...),
    channel: str | None = Form(None),
    ip_address: str | None = Form(None),
    is_enabled: str | None = Form(None),
) -> RedirectResponse:
    kwargs: dict[str, object] = {
        "name": name,
        "device_type": device_type,
        "brand": brand,
    }
    if channel:
        kwargs["channel"] = int(channel)
    if ip_address:
        kwargs["ip_address"] = ip_address
    kwargs["is_enabled"] = is_enabled == "on"

    await create_device(**kwargs)
    return RedirectResponse(url="/devices", status_code=303)


@router.get("/{device_id}", response_class=HTMLResponse)
async def device_detail(request: Request, device_id: int) -> HTMLResponse:
    from remander.main import templates

    device = await get_device(device_id)
    if device is None:
        return HTMLResponse("Device not found", status_code=404)

    await device.fetch_related("tags")
    assigned_tag_ids = {t.id for t in device.tags}
    all_tags = await list_tags()
    available_tags = [t for t in all_tags if t.id not in assigned_tag_ids]
    enabled_detection_types = {
        dt.detection_type for dt in await get_enabled_detection_types(device_id)
    }
    power_devices = await list_devices(device_type=DeviceType.POWER)
    current_power_device = (
        await get_device(device.power_device_id) if device.power_device_id else None
    )

    return templates.TemplateResponse(
        request,
        "devices/detail.html",
        {
            "device": device,
            "device_types": list(DeviceType),
            "brands": list(DeviceBrand),
            "available_tags": available_tags,
            "all_detection_types": list(DetectionType),
            "enabled_detection_types": enabled_detection_types,
            "power_devices": power_devices,
            "current_power_device": current_power_device,
            "zone_mask_error": None,
            "zone_masks_enabled_form": None,
            "zone_mask_away_form": None,
            "zone_mask_home_form": None,
        },
    )


@router.get("/{device_id}/edit", response_class=HTMLResponse)
async def device_edit_form(request: Request, device_id: int) -> RedirectResponse:
    return RedirectResponse(url=f"/devices/{device_id}", status_code=301)


@router.post("/{device_id}/edit")
async def device_edit(
    request: Request,
    device_id: int,
    name: str = Form(...),
    device_type: str = Form(...),
    brand: str = Form(...),
    channel: str | None = Form(None),
    ip_address: str | None = Form(None),
    is_enabled: str | None = Form(None),
    power_device_id: str | None = Form(None),
) -> RedirectResponse:
    kwargs: dict[str, object] = {
        "name": name,
        "device_type": device_type,
        "brand": brand,
        "is_enabled": is_enabled == "on",
    }
    if channel:
        kwargs["channel"] = int(channel)
    if ip_address:
        kwargs["ip_address"] = ip_address

    await update_device(device_id, **kwargs)

    # Set/clear power device association
    if device_type == DeviceType.CAMERA:
        await set_power_device(
            device_id, int(power_device_id) if power_device_id else None
        )

    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


@router.post("/{device_id}/zone-masks", response_model=None)
async def device_set_zone_masks(
    request: Request,
    device_id: int,
    zone_masks_enabled: str | None = Form(None),
    zone_mask_away: str = Form(default=""),
    zone_mask_home: str = Form(default=""),
) -> RedirectResponse | HTMLResponse:
    from remander.main import templates
    from remander.services.bitmask import _validate_zone_mask_value

    device = await get_device(device_id)
    if device is None:
        return HTMLResponse("Device not found", status_code=404)

    enabled = zone_masks_enabled == "on"
    error: str | None = None
    if enabled:
        try:
            _validate_zone_mask_value(zone_mask_away)
        except ValueError as e:
            error = f"Away mask: {e}"
        if error is None:
            try:
                _validate_zone_mask_value(zone_mask_home)
            except ValueError as e:
                error = f"Home mask: {e}"

    if error:
        await device.fetch_related("tags")
        assigned_tag_ids = {t.id for t in device.tags}
        all_tags = await list_tags()
        available_tags = [t for t in all_tags if t.id not in assigned_tag_ids]
        enabled_detection_types = {
            dt.detection_type for dt in await get_enabled_detection_types(device_id)
        }
        return templates.TemplateResponse(
            request,
            "devices/detail.html",
            {
                "device": device,
                "device_types": list(DeviceType),
                "brands": list(DeviceBrand),
                "available_tags": available_tags,
                "all_detection_types": list(DetectionType),
                "enabled_detection_types": enabled_detection_types,
                "zone_mask_error": error,
                "zone_masks_enabled_form": enabled,
                "zone_mask_away_form": zone_mask_away,
                "zone_mask_home_form": zone_mask_home,
            },
            status_code=422,
        )

    device.zone_masks_enabled = enabled
    device.zone_mask_away = zone_mask_away if enabled else None
    device.zone_mask_home = zone_mask_home if enabled else None
    await device.save()
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


@router.post("/{device_id}/detection-types")
async def device_set_detection_types(
    request: Request,
    device_id: int,
    detection_types: list[str] = Form(default=[]),
) -> RedirectResponse:
    valid = [DetectionType(dt) for dt in detection_types if dt in DetectionType._value2member_map_]
    await set_detection_types(device_id, valid)
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


async def _toggle_power(device_id: int, action: str) -> None:
    """Dispatch a power on/off command to the correct client.

    If the device is a power device, acts on it directly.
    If it's a camera with an associated power device, acts on that instead.
    """
    device = await get_device(device_id)
    if device is None:
        return

    if device.device_type == DeviceType.POWER:
        power_device = device
    elif device.power_device_id:
        power_device = await get_device(device.power_device_id)
    else:
        return

    if power_device is None or not power_device.ip_address:
        return

    ip = power_device.ip_address
    if power_device.brand == DeviceBrand.TAPO:
        client = TapoClient()
        if action == "on":
            await client.turn_on(ip)
        else:
            await client.turn_off(ip)
    elif power_device.brand == DeviceBrand.SONOFF:
        client = SonoffClient()
        if action == "on":
            await client.turn_on(ip)
        else:
            await client.turn_off(ip)


@router.get("/{device_id}/power/status", response_class=HTMLResponse)
async def device_power_status(request: Request, device_id: int) -> HTMLResponse:
    from remander.main import templates

    device = await get_device(device_id)
    if device is None:
        return HTMLResponse("Device not found", status_code=404)

    if device.device_type == DeviceType.POWER:
        power_device = device
    elif device.power_device_id:
        power_device = await get_device(device.power_device_id)
    else:
        return HTMLResponse("", status_code=200)

    if power_device is None or not power_device.ip_address:
        return templates.TemplateResponse(
            request,
            "devices/_power_status.html",
            {"is_on": None, "error": "No IP address configured"},
        )

    try:
        ip = power_device.ip_address
        if power_device.brand == DeviceBrand.TAPO:
            is_on = await TapoClient().is_on(ip)
        elif power_device.brand == DeviceBrand.SONOFF:
            is_on = await SonoffClient().is_on(ip)
        else:
            is_on = None
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "devices/_power_status.html",
            {"is_on": None, "error": str(e)},
        )

    return templates.TemplateResponse(
        request,
        "devices/_power_status.html",
        {"is_on": is_on, "error": None},
    )


@router.post("/{device_id}/power/on")
async def device_power_on(request: Request, device_id: int) -> RedirectResponse:
    await _toggle_power(device_id, "on")
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


@router.post("/{device_id}/power/off")
async def device_power_off(request: Request, device_id: int) -> RedirectResponse:
    await _toggle_power(device_id, "off")
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


@router.post("/{device_id}/ptz-settings")
async def device_ptz_settings(
    request: Request,
    device_id: int,
    has_ptz: str | None = Form(None),
    ptz_away_preset: str | None = Form(None),
    ptz_home_preset: str | None = Form(None),
    ptz_speed: str | None = Form(None),
) -> RedirectResponse:
    device = await get_device(device_id)
    if device is None:
        return HTMLResponse("Device not found", status_code=404)

    enabled = has_ptz == "on"
    device.has_ptz = enabled
    if enabled:
        device.ptz_away_preset = int(ptz_away_preset) if ptz_away_preset else None
        device.ptz_home_preset = int(ptz_home_preset) if ptz_home_preset else None
        device.ptz_speed = int(ptz_speed) if ptz_speed else None
    else:
        device.ptz_away_preset = None
        device.ptz_home_preset = None
        device.ptz_speed = None
    await device.save()
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


@router.post("/{device_id}/query-ptz-presets", response_class=HTMLResponse)
async def device_query_ptz_presets(request: Request, device_id: int) -> HTMLResponse:
    from remander.config import get_settings
    from remander.main import templates

    device = await get_device(device_id)
    if device is None:
        return HTMLResponse("Device not found", status_code=404)

    if device.channel is None:
        return templates.TemplateResponse(
            request,
            "devices/_ptz_presets.html",
            {"presets": None, "error": "Device has no channel configured."},
        )

    settings = get_settings()
    client = ReolinkNVRClient(
        host=settings.nvr_host,
        port=settings.nvr_port,
        username=settings.nvr_username,
        password=settings.nvr_password.get_secret_value(),
        use_https=settings.nvr_use_https,
        timeout=settings.nvr_timeout,
    )

    try:
        await asyncio.wait_for(client.login(), timeout=settings.nvr_timeout)
        presets = client.get_ptz_presets(device.channel)
        await client.logout()
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "devices/_ptz_presets.html",
            {"presets": None, "error": str(e)},
        )

    return templates.TemplateResponse(
        request,
        "devices/_ptz_presets.html",
        {"presets": presets, "error": None},
    )


@router.post("/{device_id}/delete")
async def device_delete(request: Request, device_id: int) -> RedirectResponse:
    await delete_device(device_id)
    return RedirectResponse(url="/devices", status_code=303)
