"""Factory functions for HourBitmask and ZoneMask model instances."""

from uuid import uuid4

from remander.models.bitmask import HourBitmask, ZoneMask
from remander.models.enums import HourBitmaskSubtype


async def create_hour_bitmask(**kwargs: object) -> HourBitmask:
    """Create an HourBitmask with sensible defaults (static, all-ones)."""
    defaults: dict[str, object] = {
        "name": f"Bitmask {uuid4().hex[:6]}",
        "subtype": HourBitmaskSubtype.STATIC,
        "static_value": "1" * 24,
    }
    defaults.update(kwargs)
    return await HourBitmask.create(**defaults)


async def create_dynamic_hour_bitmask(**kwargs: object) -> HourBitmask:
    """Create a dynamic HourBitmask with sunrise/sunset defaults."""
    defaults: dict[str, object] = {
        "name": f"Dynamic Bitmask {uuid4().hex[:6]}",
        "subtype": HourBitmaskSubtype.DYNAMIC,
        "sunrise_offset_minutes": 0,
        "sunset_offset_minutes": 0,
        "fill_value": "1",
    }
    defaults.update(kwargs)
    return await HourBitmask.create(**defaults)


async def create_zone_mask(**kwargs: object) -> ZoneMask:
    """Create a ZoneMask with sensible defaults (all-ones, full detection area)."""
    defaults: dict[str, object] = {
        "name": f"Zone {uuid4().hex[:6]}",
        "mask_value": "1" * 4800,
    }
    defaults.update(kwargs)
    return await ZoneMask.create(**defaults)
