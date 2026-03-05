"""NVR sync service — compare NVR channel data against existing devices."""

import attrs

from remander.models.device import Device
from remander.models.enums import ChannelSyncStatus, DeviceBrand, DeviceType

# NVR key → Device attribute mapping for comparison
_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "model": "model_name",
    "hw_version": "hw_version",
    "firmware": "firmware",
}


def _normalize(value: str | None) -> str:
    """Treat None and empty string as equivalent for comparison."""
    return value or ""


@attrs.define(frozen=True)
class FieldDiff:
    """A single field difference between NVR data and an existing device."""

    field_name: str
    nvr_value: str | None
    db_value: str | None


@attrs.define(frozen=True)
class ChannelSyncResult:
    """Comparison result for one NVR channel against existing devices."""

    channel: int
    name: str | None
    model: str | None
    hw_version: str | None
    firmware: str | None
    online: bool
    status: ChannelSyncStatus
    device_id: int | None = None
    diffs: tuple[FieldDiff, ...] = ()


def compare_channels(
    nvr_channels: list[dict], existing_devices: list[Device]
) -> list[ChannelSyncResult]:
    """Compare NVR channel data against existing devices by channel number.

    Pure function — no database access.
    """
    device_by_channel: dict[int, Device] = {
        d.channel: d for d in existing_devices if d.channel is not None
    }
    results: list[ChannelSyncResult] = []

    for ch in nvr_channels:
        channel_num = ch["channel"]
        device = device_by_channel.get(channel_num)

        if device is None:
            results.append(
                ChannelSyncResult(
                    channel=channel_num,
                    name=ch.get("name"),
                    model=ch.get("model"),
                    hw_version=ch.get("hw_version"),
                    firmware=ch.get("firmware"),
                    online=ch.get("online", False),
                    status=ChannelSyncStatus.NEW,
                )
            )
        else:
            diffs: list[FieldDiff] = []
            for nvr_key, device_attr in _FIELD_MAP.items():
                nvr_val = ch.get(nvr_key)
                db_val = getattr(device, device_attr)
                if _normalize(nvr_val) != _normalize(db_val):
                    diffs.append(
                        FieldDiff(field_name=device_attr, nvr_value=nvr_val, db_value=db_val)
                    )

            status = ChannelSyncStatus.CHANGED if diffs else ChannelSyncStatus.OK
            results.append(
                ChannelSyncResult(
                    channel=channel_num,
                    name=ch.get("name"),
                    model=ch.get("model"),
                    hw_version=ch.get("hw_version"),
                    firmware=ch.get("firmware"),
                    online=ch.get("online", False),
                    status=status,
                    device_id=device.id,
                    diffs=tuple(diffs),
                )
            )

    return results


async def create_device_from_channel(channel_data: dict) -> Device:
    """Create a new Device from NVR channel data (type=CAMERA, brand=REOLINK)."""
    return await Device.create(
        name=channel_data["name"],
        channel=channel_data["channel"],
        device_type=DeviceType.CAMERA,
        brand=DeviceBrand.REOLINK,
        model_name=channel_data.get("model"),
        hw_version=channel_data.get("hw_version"),
        firmware=channel_data.get("firmware"),
    )


async def update_device_from_channel(device_id: int, channel_data: dict) -> Device | None:
    """Update an existing device's name/model/hw_version/firmware from NVR data.

    Returns the updated device, or None if the device doesn't exist.
    """
    device = await Device.get_or_none(id=device_id)
    if device is None:
        return None

    device.name = channel_data["name"]
    device.model_name = channel_data.get("model")
    device.hw_version = channel_data.get("hw_version")
    device.firmware = channel_data.get("firmware")
    await device.save()
    return device


async def sync_all_channels(
    nvr_channels: list[dict], existing_devices: list[Device]
) -> tuple[int, int]:
    """Bulk create new devices and update changed ones.

    Returns (created_count, updated_count).
    """
    sync_results = compare_channels(nvr_channels, existing_devices)
    created = 0
    updated = 0

    for result in sync_results:
        channel_data = {
            "channel": result.channel,
            "name": result.name,
            "model": result.model,
            "hw_version": result.hw_version,
            "firmware": result.firmware,
        }
        if result.status == ChannelSyncStatus.NEW:
            await create_device_from_channel(channel_data)
            created += 1
        elif result.status == ChannelSyncStatus.CHANGED and result.device_id is not None:
            await update_device_from_channel(result.device_id, channel_data)
            updated += 1

    return created, updated
