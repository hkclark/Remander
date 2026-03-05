"""Device route handlers — list, detail, create, edit, delete."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.models.enums import DeviceBrand, DeviceType
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

    return templates.TemplateResponse(
        request,
        "devices/detail.html",
        {"device": device, "available_tags": available_tags},
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


@router.post("/{device_id}/delete")
async def device_delete(request: Request, device_id: int) -> RedirectResponse:
    await delete_device(device_id)
    return RedirectResponse(url="/devices", status_code=303)
