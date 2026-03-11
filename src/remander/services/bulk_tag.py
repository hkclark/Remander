"""Bulk tag service — channel spec parsing, device matching, and bulk tag operations."""

import fnmatch

from remander.models.device import Device
from remander.models.tag import Tag


def parse_channel_spec(spec: str) -> set[int]:
    """Parse a channel specifier string into a set of integers.

    Supports:
    - Single numbers:      "1"
    - Comma-separated:     "1, 2, 3"
    - Ranges (inclusive):  "2-4"
    - Mixed:               "2-4, 6, 8-9"
    """
    spec = spec.strip()
    if not spec:
        return set()

    result: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            halves = part.split("-", 1)
            try:
                start = int(halves[0].strip())
                end = int(halves[1].strip())
            except ValueError:
                raise ValueError(f"Invalid channel range: {part!r}")
            if start > end:
                raise ValueError(f"Invalid range: start {start} > end {end}")
            result.update(range(start, end + 1))
        else:
            try:
                result.add(int(part))
            except ValueError:
                raise ValueError(f"Invalid channel number: {part!r}")
    return result


def find_devices_for_bulk(
    devices: list[Device],
    *,
    name_pattern: str = "",
    channel_spec: set[int] | None = None,
) -> list[Device]:
    """Filter devices by name wildcard and/or channel spec.

    Both filters are optional. When both are provided, devices must satisfy both.
    Name matching uses fnmatch glob syntax (case-insensitive).
    Channel filtering only matches devices that have a channel set.
    """
    result = []
    for device in devices:
        if name_pattern:
            if not fnmatch.fnmatch(device.name.lower(), name_pattern.lower()):
                continue
        if channel_spec:
            if device.channel is None or device.channel not in channel_spec:
                continue
        result.append(device)
    return result


async def bulk_tag_devices(device_ids: list[int], tag_id: int) -> int:
    """Add a tag to multiple devices. Returns the number of devices tagged."""
    tag = await Tag.get(id=tag_id)
    count = 0
    for device_id in device_ids:
        device = await Device.get_or_none(id=device_id)
        if device:
            await device.tags.add(tag)
            count += 1
    return count


async def bulk_untag_devices(device_ids: list[int], tag_id: int) -> int:
    """Remove a tag from multiple devices. Returns the number of devices untagged."""
    tag = await Tag.get_or_none(id=tag_id)
    if tag is None:
        return 0
    count = 0
    for device_id in device_ids:
        device = await Device.get_or_none(id=device_id)
        if device:
            await device.tags.remove(tag)
            count += 1
    return count
