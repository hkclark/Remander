"""Bitmask route handlers — hour bitmasks and zone masks."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.models.bitmask import HourBitmask
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
    resolve_hour_bitmask,
    update_hour_bitmask,
)
from remander.services.solar import get_sunrise_sunset

router = APIRouter(prefix="/bitmasks")


async def _location_form_context() -> dict:
    """Build location/sunrise/sunset context for the hour bitmask create and edit forms."""
    from remander.config import get_settings

    settings = get_settings()
    location_sunrise: str | None = None
    location_sunset: str | None = None
    location_sunrise_minutes: int | None = None
    location_sunset_minutes: int | None = None

    if settings.latitude != 0.0 or settings.longitude != 0.0:
        try:
            sr, ss = await get_sunrise_sunset(
                settings.latitude, settings.longitude, timezone=settings.timezone
            )
            location_sunrise = sr.strftime("%-I:%M %p")
            location_sunset = ss.strftime("%-I:%M %p")
            location_sunrise_minutes = sr.hour * 60 + sr.minute
            location_sunset_minutes = ss.hour * 60 + ss.minute
        except Exception:
            pass

    return {
        "location_lat": settings.latitude,
        "location_lon": settings.longitude,
        "location_timezone": settings.timezone,
        "location_sunrise": location_sunrise,
        "location_sunset": location_sunset,
        "location_sunrise_minutes": location_sunrise_minutes,
        "location_sunset_minutes": location_sunset_minutes,
    }


@router.get("", response_class=HTMLResponse)
async def bitmask_list(request: Request) -> HTMLResponse:
    from remander.config import get_settings
    from remander.main import templates

    hour_bitmasks = await list_hour_bitmasks()
    zone_masks = await list_zone_masks()

    settings = get_settings()
    dynamic_computed: dict[int, str] = {}
    for bm in hour_bitmasks:
        if bm.subtype == HourBitmaskSubtype.DYNAMIC:
            dynamic_computed[bm.id] = await resolve_hour_bitmask(
                bm,
                latitude=settings.latitude,
                longitude=settings.longitude,
                timezone=settings.timezone,
            )

    has_dynamic = any(bm.subtype == HourBitmaskSubtype.DYNAMIC for bm in hour_bitmasks)
    timezone_warning = has_dynamic and settings.timezone == "UTC" and (
        settings.latitude != 0.0 or settings.longitude != 0.0
    )

    # Compute today's sunrise/sunset for the diagnostic card (only if lat/lon are non-zero)
    location_sunrise: str | None = None
    location_sunset: str | None = None
    if settings.latitude != 0.0 or settings.longitude != 0.0:
        try:
            sr, ss = await get_sunrise_sunset(
                settings.latitude,
                settings.longitude,
                timezone=settings.timezone,
            )
            location_sunrise = sr.strftime("%-I:%M %p")
            location_sunset = ss.strftime("%-I:%M %p")
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "bitmasks/list.html",
        {
            "hour_bitmasks": hour_bitmasks,
            "zone_masks": zone_masks,
            "dynamic_computed": dynamic_computed,
            "timezone_warning": timezone_warning,
            "current_timezone": settings.timezone,
            "location_lat": settings.latitude,
            "location_lon": settings.longitude,
            "location_sunrise": location_sunrise,
            "location_sunset": location_sunset,
        },
    )


# --- Hour Bitmask routes ---


@router.get("/hour/create", response_class=HTMLResponse)
async def hour_bitmask_create_form(request: Request) -> HTMLResponse:
    from remander.main import templates

    location_ctx = await _location_form_context()
    return templates.TemplateResponse(
        request,
        "bitmasks/hour_form.html",
        {"bitmask": None, "subtypes": list(HourBitmaskSubtype), **location_ctx},
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

    location_ctx = await _location_form_context()
    return templates.TemplateResponse(
        request,
        "bitmasks/hour_form.html",
        {"bitmask": bitmask, "subtypes": list(HourBitmaskSubtype), **location_ctx},
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
