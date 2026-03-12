"""Device service — CRUD operations for cameras and power devices."""

from remander.models.device import Device
from remander.models.enums import DeviceType


def _device_sort_key(device: Device) -> tuple:
    """Sort key: device type (cameras first), channel (nulls last), name case-insensitive."""
    type_order = 0 if device.device_type == DeviceType.CAMERA else 1
    channel = device.channel if device.channel is not None else float("inf")
    return (type_order, channel, device.name.lower())


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
    prefetch: list[str] | None = None,
    sorted_for_display: bool = False,
) -> list[Device]:
    """List devices with optional filters.

    Pass sorted_for_display=True to sort by type (cameras first), channel, then name.
    """
    qs = Device.all()
    if device_type is not None:
        qs = qs.filter(device_type=device_type)
    if is_enabled is not None:
        qs = qs.filter(is_enabled=is_enabled)
    if prefetch:
        qs = qs.prefetch_related(*prefetch)
    devices = await qs
    if sorted_for_display:
        devices = sorted(devices, key=_device_sort_key)
    return devices


async def get_devices_missing_detection_types(
    device_ids: list[int] | None = None,
) -> list[Device]:
    """Return enabled camera devices that have a channel but no enabled DetectionType records.

    These devices are silently skipped during bitmask operations, so this list is
    used to warn the user before a command runs.

    If device_ids is provided, only those devices are checked (used to scope the
    warning to the devices a specific button operates on).
    """
    from remander.models.detection import DeviceDetectionType

    qs = Device.filter(is_enabled=True, device_type=DeviceType.CAMERA).exclude(channel=None)
    if device_ids is not None:
        qs = qs.filter(id__in=device_ids)
    cameras = await qs
    missing = []
    for device in cameras:
        count = await DeviceDetectionType.filter(device_id=device.id, is_enabled=True).count()
        if count == 0:
            missing.append(device)
    return missing


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
