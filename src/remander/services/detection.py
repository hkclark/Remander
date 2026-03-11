"""Detection type service — manage which detection types a device supports."""

from collections.abc import Collection

from remander.models.detection import DeviceDetectionType
from remander.models.enums import DetectionType

_AI_TYPES: frozenset[DetectionType] = frozenset(
    {DetectionType.PERSON, DetectionType.VEHICLE, DetectionType.ANIMAL, DetectionType.FACE, DetectionType.PACKAGE}
)


def has_ai_and_md(types: Collection[DetectionType]) -> bool:
    """True when both MOTION and at least one AI detection type are present."""
    type_set = frozenset(types)
    return DetectionType.MOTION in type_set and bool(type_set & _AI_TYPES)


def has_ai(types: Collection[DetectionType]) -> bool:
    """True when at least one AI detection type is present and MOTION is not."""
    type_set = frozenset(types)
    return bool(type_set & _AI_TYPES) and DetectionType.MOTION not in type_set


def has_md(types: Collection[DetectionType]) -> bool:
    """True when MOTION is present and no AI detection types are present."""
    type_set = frozenset(types)
    return DetectionType.MOTION in type_set and not (type_set & _AI_TYPES)


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
