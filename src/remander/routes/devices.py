"""Device route handlers — list, detail, create, edit, delete."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.models.enums import DetectionType, DeviceBrand, DeviceType
from remander.services.detection import get_enabled_detection_types, set_detection_types
from remander.services.device import (
    create_device,
    delete_device,
    get_device,
    list_devices,
    update_device,
)
from remander.services.tag import list_tags

router = APIRouter(prefix="/devices")


@router.get("", response_class=HTMLResponse)
async def device_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    devices = await list_devices(prefetch=["tags"])
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

    return templates.TemplateResponse(
        request,
        "devices/detail.html",
        {
            "device": device,
            "available_tags": available_tags,
            "all_detection_types": list(DetectionType),
            "enabled_detection_types": enabled_detection_types,
            "zone_mask_error": None,
            "zone_masks_enabled_form": None,
            "zone_mask_away_form": None,
            "zone_mask_home_form": None,
        },
    )


@router.get("/{device_id}/edit", response_class=HTMLResponse)
async def device_edit_form(request: Request, device_id: int) -> HTMLResponse:
    from remander.main import templates

    device = await get_device(device_id)
    if device is None:
        return HTMLResponse("Device not found", status_code=404)

    return templates.TemplateResponse(
        request,
        "devices/form.html",
        {
            "device": device,
            "device_types": list(DeviceType),
            "brands": list(DeviceBrand),
        },
    )


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


@router.post("/{device_id}/delete")
async def device_delete(request: Request, device_id: int) -> RedirectResponse:
    await delete_device(device_id)
    return RedirectResponse(url="/devices", status_code=303)
