"""Factory functions for Device model instances."""

from uuid import uuid4

from remander.models.device import Device
from remander.models.enums import DeviceBrand, DeviceType, PowerDeviceSubtype


async def create_device(**kwargs: object) -> Device:
    """Create a Device with sensible defaults. Override any field via kwargs."""
    defaults: dict[str, object] = {
        "name": f"Device {uuid4().hex[:6]}",
        "device_type": DeviceType.CAMERA,
        "brand": DeviceBrand.REOLINK,
        "is_enabled": True,
    }
    defaults.update(kwargs)
    return await Device.create(**defaults)


async def create_camera(**kwargs: object) -> Device:
    """Create a camera device with camera-specific defaults."""
    defaults: dict[str, object] = {
        "device_type": DeviceType.CAMERA,
        "brand": DeviceBrand.REOLINK,
        "channel": 0,
    }
    defaults.update(kwargs)
    return await create_device(**defaults)


async def create_power_device(**kwargs: object) -> Device:
    """Create a power device with power-specific defaults."""
    defaults: dict[str, object] = {
        "device_type": DeviceType.POWER,
        "brand": DeviceBrand.TAPO,
        "device_subtype": PowerDeviceSubtype.SMART_PLUG,
        "ip_address": "192.168.1.200",
    }
    defaults.update(kwargs)
    return await create_device(**defaults)
