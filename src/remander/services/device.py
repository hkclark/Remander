"""Device service — CRUD operations for cameras and power devices."""

from remander.models.device import Device
from remander.models.enums import DeviceType


async def create_device(**kwargs: object) -> Device:
    """Create a new device (camera or power device)."""
    return await Device.create(**kwargs)


async def get_device(device_id: int) -> Device | None:
    """Fetch a device by ID, or None if not found.

    Tags and detection types are accessible via their reverse relations on the returned instance.
    """
    return await Device.get_or_none(id=device_id)


async def list_devices(
    *,
    device_type: DeviceType | None = None,
    is_enabled: bool | None = None,
) -> list[Device]:
    """List devices with optional filters."""
    qs = Device.all()
    if device_type is not None:
        qs = qs.filter(device_type=device_type)
    if is_enabled is not None:
        qs = qs.filter(is_enabled=is_enabled)
    return await qs


async def update_device(device_id: int, **kwargs: object) -> Device | None:
    """Update device fields. Returns the updated device, or None if not found."""
    device = await Device.get_or_none(id=device_id)
    if device is None:
        return None
    await device.update_from_dict(kwargs).save()
    return device


async def delete_device(device_id: int) -> bool:
    """Delete a device by ID. Returns True if deleted, False if not found."""
    device = await Device.get_or_none(id=device_id)
    if device is None:
        return False
    await device.delete()
    return True


async def set_power_device(camera_id: int, power_device_id: int | None) -> Device | None:
    """Associate a camera with a power device, or clear the association (None)."""
    camera = await Device.get_or_none(id=camera_id)
    if camera is None:
        return None
    camera.power_device_id = power_device_id
    await camera.save()
    return camera


async def get_cameras_with_power_devices() -> list[Device]:
    """List cameras that have an associated power device."""
    return await Device.filter(
        device_type=DeviceType.CAMERA,
        power_device_id__isnull=False,
    )
