"""Bitmask route handlers — hour bitmasks and zone masks."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.models.enums import HourBitmaskSubtype
from remander.services.bitmask import (
    create_hour_bitmask,
    create_zone_mask,
    delete_hour_bitmask,
    delete_zone_mask,
    get_hour_bitmask,
    get_zone_mask,
    list_hour_bitmasks,
    list_zone_masks,
    update_hour_bitmask,
)

router = APIRouter(prefix="/bitmasks")


@router.get("", response_class=HTMLResponse)
async def bitmask_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    hour_bitmasks = await list_hour_bitmasks()
    zone_masks = await list_zone_masks()
    return templates.TemplateResponse(
        request,
        "bitmasks/list.html",
        {"hour_bitmasks": hour_bitmasks, "zone_masks": zone_masks},
    )


# --- Hour Bitmask routes ---


@router.get("/hour/create", response_class=HTMLResponse)
async def hour_bitmask_create_form(request: Request) -> HTMLResponse:
    from remander.main import templates

    return templates.TemplateResponse(
        request,
        "bitmasks/hour_form.html",
        {"bitmask": None, "subtypes": list(HourBitmaskSubtype)},
    )


@router.post("/hour/create")
async def hour_bitmask_create(
    request: Request,
    name: str = Form(...),
    subtype: str = Form(...),
    static_value: str | None = Form(None),
    sunrise_offset_minutes: str | None = Form(None),
    sunset_offset_minutes: str | None = Form(None),
    fill_value: str | None = Form(None),
) -> RedirectResponse:
    kwargs: dict[str, object] = {
        "name": name,
        "subtype": HourBitmaskSubtype(subtype),
    }
    if subtype == "static":
        kwargs["static_value"] = static_value
    else:
        if sunrise_offset_minutes:
            kwargs["sunrise_offset_minutes"] = int(sunrise_offset_minutes)
        if sunset_offset_minutes:
            kwargs["sunset_offset_minutes"] = int(sunset_offset_minutes)
        kwargs["fill_value"] = fill_value or "1"

    await create_hour_bitmask(**kwargs)
    return RedirectResponse(url="/bitmasks", status_code=303)


@router.get("/hour/{bitmask_id}", response_class=HTMLResponse)
async def hour_bitmask_detail(request: Request, bitmask_id: int) -> HTMLResponse:
    from remander.main import templates

    bitmask = await get_hour_bitmask(bitmask_id)
    if bitmask is None:
        return HTMLResponse("Hour bitmask not found", status_code=404)

    return templates.TemplateResponse(
        request,
        "bitmasks/hour_detail.html",
        {"bitmask": bitmask},
    )


@router.get("/hour/{bitmask_id}/edit", response_class=HTMLResponse)
async def hour_bitmask_edit_form(request: Request, bitmask_id: int) -> HTMLResponse:
    from remander.main import templates

    bitmask = await get_hour_bitmask(bitmask_id)
    if bitmask is None:
        return HTMLResponse("Hour bitmask not found", status_code=404)

    return templates.TemplateResponse(
        request,
        "bitmasks/hour_form.html",
        {"bitmask": bitmask, "subtypes": list(HourBitmaskSubtype)},
    )


@router.post("/hour/{bitmask_id}/edit")
async def hour_bitmask_edit(
    request: Request,
    bitmask_id: int,
    name: str = Form(...),
    subtype: str = Form(...),
    static_value: str | None = Form(None),
    sunrise_offset_minutes: str | None = Form(None),
    sunset_offset_minutes: str | None = Form(None),
    fill_value: str | None = Form(None),
) -> RedirectResponse:
    kwargs: dict[str, object] = {
        "name": name,
        "subtype": HourBitmaskSubtype(subtype),
    }
    if subtype == "static":
        kwargs["static_value"] = static_value
    else:
        if sunrise_offset_minutes:
            kwargs["sunrise_offset_minutes"] = int(sunrise_offset_minutes)
        if sunset_offset_minutes:
            kwargs["sunset_offset_minutes"] = int(sunset_offset_minutes)
        kwargs["fill_value"] = fill_value or "1"

    await update_hour_bitmask(bitmask_id, **kwargs)
    return RedirectResponse(url=f"/bitmasks/hour/{bitmask_id}", status_code=303)


@router.post("/hour/{bitmask_id}/delete")
async def hour_bitmask_delete(request: Request, bitmask_id: int) -> RedirectResponse:
    await delete_hour_bitmask(bitmask_id)
    return RedirectResponse(url="/bitmasks", status_code=303)


# --- Zone Mask routes ---


@router.get("/zone/create", response_class=HTMLResponse)
async def zone_mask_create_form(request: Request) -> HTMLResponse:
    from remander.main import templates

    return templates.TemplateResponse(
        request,
        "bitmasks/zone_form.html",
        {"zone_mask": None},
    )


@router.post("/zone/create")
async def zone_mask_create(
    request: Request,
    name: str = Form(...),
    mask_value: str = Form(...),
) -> RedirectResponse:
    await create_zone_mask(name=name, mask_value=mask_value)
    return RedirectResponse(url="/bitmasks", status_code=303)


@router.get("/zone/{mask_id}", response_class=HTMLResponse)
async def zone_mask_detail(request: Request, mask_id: int) -> HTMLResponse:
    from remander.main import templates

    zone_mask = await get_zone_mask(mask_id)
    if zone_mask is None:
        return HTMLResponse("Zone mask not found", status_code=404)

    return templates.TemplateResponse(
        request,
        "bitmasks/zone_detail.html",
        {"zone_mask": zone_mask},
    )


@router.post("/zone/{mask_id}/delete")
async def zone_mask_delete(request: Request, mask_id: int) -> RedirectResponse:
    await delete_zone_mask(mask_id)
    return RedirectResponse(url="/bitmasks", status_code=303)
