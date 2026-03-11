"""Bitmask service — CRUD for hour bitmasks, zone masks, assignments, and resolution."""

import re

from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask, ZoneMask
from remander.models.detection import DeviceDetectionType
from remander.models.enums import DetectionType, HourBitmaskSubtype, Mode
from remander.services.solar import compute_dynamic_bitmask, get_sunrise_sunset

BITMASK_PATTERN = re.compile(r"^[01]+$")


def _validate_hour_bitmask_value(value: str) -> None:
    if len(value) != 24:
        raise ValueError(f"Hour bitmask must be exactly 24 characters, got {len(value)}")
    if not BITMASK_PATTERN.match(value):
        raise ValueError("Hour bitmask must contain only 0 and 1 characters")


def _validate_zone_mask_value(value: str) -> None:
    if len(value) != 4800:
        raise ValueError(f"Zone mask must be exactly 4800 characters, got {len(value)}")
    if not BITMASK_PATTERN.match(value):
        raise ValueError("Zone mask must contain only 0 and 1 characters")


# --- Hour Bitmask CRUD ---


async def create_hour_bitmask(
    name: str,
    subtype: HourBitmaskSubtype,
    static_value: str | None = None,
    sunrise_offset_minutes: int | None = None,
    sunset_offset_minutes: int | None = None,
    fill_value: str | None = None,
) -> HourBitmask:
    """Create a new hour bitmask with validation."""
    if subtype == HourBitmaskSubtype.STATIC and static_value is not None:
        _validate_hour_bitmask_value(static_value)
    return await HourBitmask.create(
        name=name,
        subtype=subtype,
        static_value=static_value,
        sunrise_offset_minutes=sunrise_offset_minutes,
        sunset_offset_minutes=sunset_offset_minutes,
        fill_value=fill_value,
    )


async def get_hour_bitmask(bitmask_id: int) -> HourBitmask | None:
    return await HourBitmask.get_or_none(id=bitmask_id)


async def list_hour_bitmasks() -> list[HourBitmask]:
    return await HourBitmask.all()


async def update_hour_bitmask(bitmask_id: int, **kwargs: object) -> HourBitmask | None:
    bm = await HourBitmask.get_or_none(id=bitmask_id)
    if bm is None:
        return None
    if "static_value" in kwargs and kwargs["static_value"] is not None:
        _validate_hour_bitmask_value(str(kwargs["static_value"]))
    await bm.update_from_dict(kwargs).save()
    return bm


async def delete_hour_bitmask(bitmask_id: int) -> bool:
    bm = await HourBitmask.get_or_none(id=bitmask_id)
    if bm is None:
        return False
    await bm.delete()
    return True


# --- Zone Mask CRUD ---


async def create_zone_mask(name: str, mask_value: str) -> ZoneMask:
    """Create a new zone mask with validation."""
    _validate_zone_mask_value(mask_value)
    return await ZoneMask.create(name=name, mask_value=mask_value)


async def get_zone_mask(mask_id: int) -> ZoneMask | None:
    return await ZoneMask.get_or_none(id=mask_id)


async def list_zone_masks() -> list[ZoneMask]:
    return await ZoneMask.all()


async def update_zone_mask(mask_id: int, **kwargs: object) -> ZoneMask | None:
    zm = await ZoneMask.get_or_none(id=mask_id)
    if zm is None:
        return None
    if "mask_value" in kwargs and kwargs["mask_value"] is not None:
        _validate_zone_mask_value(str(kwargs["mask_value"]))
    await zm.update_from_dict(kwargs).save()
    return zm


async def delete_zone_mask(mask_id: int) -> bool:
    zm = await ZoneMask.get_or_none(id=mask_id)
    if zm is None:
        return False
    await zm.delete()
    return True


# --- Bitmask Assignment CRUD ---


async def assign_bitmask(
    device_id: int,
    mode: Mode,
    detection_type: DetectionType,
    hour_bitmask_id: int | None = None,
    zone_mask_id: int | None = None,
) -> DeviceBitmaskAssignment:
    """Create or update a bitmask assignment for a device+mode+detection_type."""
    assignment, _ = await DeviceBitmaskAssignment.update_or_create(
        defaults={"hour_bitmask_id": hour_bitmask_id, "zone_mask_id": zone_mask_id},
        device_id=device_id,
        mode=mode,
        detection_type=detection_type,
    )
    return assignment


async def get_assignments_for_device(
    device_id: int, mode: Mode | None = None
) -> list[DeviceBitmaskAssignment]:
    qs = DeviceBitmaskAssignment.filter(device_id=device_id)
    if mode is not None:
        qs = qs.filter(mode=mode)
    return await qs


async def delete_assignment(assignment_id: int) -> bool:
    assignment = await DeviceBitmaskAssignment.get_or_none(id=assignment_id)
    if assignment is None:
        return False
    await assignment.delete()
    return True


# --- Bitmask Resolution ---


async def resolve_hour_bitmask(
    hour_bitmask: HourBitmask,
    *,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone: str = "UTC",
) -> str:
    """Resolve an hour bitmask to its 24-char value.

    Static: returns static_value directly.
    Dynamic: calculates from sunrise/sunset using the configured location and timezone.
    """
    if hour_bitmask.subtype == HourBitmaskSubtype.STATIC:
        return hour_bitmask.static_value or "0" * 24

    sunrise, sunset = await get_sunrise_sunset(latitude, longitude, timezone=timezone)
    return compute_dynamic_bitmask(
        sunrise,
        sunset,
        sunrise_offset_minutes=hour_bitmask.sunrise_offset_minutes or 0,
        sunset_offset_minutes=hour_bitmask.sunset_offset_minutes or 0,
        fill_value=hour_bitmask.fill_value or "1",
    )


async def resolve_bitmasks_for_device(
    device_id: int,
    mode: Mode,
    *,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone: str = "UTC",
) -> list[dict]:
    """Resolve hour bitmask + zone mask per enabled detection type for a device in a given mode.

    Returns a list of dicts: [{detection_type, hour_bitmask, zone_mask}, ...]
    """
    from remander.models.device import Device

    device = await Device.get(id=device_id)
    enabled_types = await DeviceDetectionType.filter(device_id=device_id, is_enabled=True)
    if not enabled_types:
        return []

    # Zone mask value for this mode: None means "disabled, skip zone mask entirely"
    if device.zone_masks_enabled:
        zone_value: str | None = (
            device.zone_mask_away if mode == Mode.AWAY else device.zone_mask_home
        )
    else:
        zone_value = None

    results = []
    for dt_record in enabled_types:
        detection_type = dt_record.detection_type

        assignment = await DeviceBitmaskAssignment.get_or_none(
            device_id=device_id, mode=mode, detection_type=detection_type
        )

        if assignment is not None and assignment.hour_bitmask_id is not None:
            hb = await HourBitmask.get(id=assignment.hour_bitmask_id)
            hour_value = await resolve_hour_bitmask(
                hb, latitude=latitude, longitude=longitude, timezone=timezone
            )
        else:
            hour_value = "0" * 24

        results.append(
            {
                "detection_type": detection_type,
                "hour_bitmask": hour_value,
                "zone_mask": zone_value,
            }
        )

    return results


async def find_devices_missing_bitmasks(device_ids: list[int], mode: Mode) -> list:
    """Return enabled camera devices (channel is set) with no hour bitmask assignment for mode.

    Used to block command execution when devices aren't fully configured.
    """
    from remander.models.device import Device

    missing = []
    for device_id in device_ids:
        device = await Device.get_or_none(id=device_id)
        if device is None or device.channel is None:
            continue
        has_assignment = (
            await DeviceBitmaskAssignment.filter(device_id=device_id, mode=mode)
            .exclude(hour_bitmask_id=None)
            .exists()
        )
        if not has_assignment:
            missing.append(device)
    return missing
