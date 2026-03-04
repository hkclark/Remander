"""Detection type service — manage which detection types a device supports."""

from remander.models.detection import DeviceDetectionType
from remander.models.enums import DetectionType


async def set_detection_types(device_id: int, detection_types: list[DetectionType]) -> None:
    """Bulk set which detection types a device supports. Replaces any existing types."""
    await DeviceDetectionType.filter(device_id=device_id).delete()
    for dt in detection_types:
        await DeviceDetectionType.create(device_id=device_id, detection_type=dt, is_enabled=True)


async def enable_detection_type(device_id: int, detection_type: DetectionType) -> None:
    """Enable a specific detection type for a device."""
    await DeviceDetectionType.filter(device_id=device_id, detection_type=detection_type).update(
        is_enabled=True
    )


async def disable_detection_type(device_id: int, detection_type: DetectionType) -> None:
    """Disable a specific detection type for a device."""
    await DeviceDetectionType.filter(device_id=device_id, detection_type=detection_type).update(
        is_enabled=False
    )


async def get_enabled_detection_types(device_id: int) -> list[DeviceDetectionType]:
    """List all enabled detection types for a device."""
    return await DeviceDetectionType.filter(device_id=device_id, is_enabled=True)
