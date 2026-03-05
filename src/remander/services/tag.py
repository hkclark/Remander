"""Tag service — CRUD operations for tags and device-tag associations."""

from tortoise.functions import Count

from remander.models.device import Device
from remander.models.tag import Tag


async def create_tag(name: str, *, show_on_dashboard: bool = False) -> Tag:
    """Create a new tag."""
    return await Tag.create(name=name, show_on_dashboard=show_on_dashboard)


async def list_tags() -> list[Tag]:
    """List all tags with device counts (annotated as `device_count`)."""
    return await Tag.all().annotate(device_count=Count("devices"))


async def update_tag(
    tag_id: int,
    *,
    name: str | None = None,
    show_on_dashboard: bool | None = None,
) -> Tag | None:
    """Update a tag's name and/or dashboard flag. Returns None if not found."""
    tag = await Tag.get_or_none(id=tag_id)
    if tag is None:
        return None
    if name is not None:
        tag.name = name
    if show_on_dashboard is not None:
        tag.show_on_dashboard = show_on_dashboard
    await tag.save()
    return tag


async def delete_tag(tag_id: int) -> bool:
    """Delete a tag by ID. Returns True if deleted, False if not found."""
    tag = await Tag.get_or_none(id=tag_id)
    if tag is None:
        return False
    await tag.delete()
    return True


async def list_dashboard_tags() -> list[Tag]:
    """List tags flagged for display on the dashboard pause section."""
    return await Tag.filter(show_on_dashboard=True).order_by("name")


async def add_tag_to_device(device_id: int, tag_id: int) -> None:
    """Add a tag to a device. Idempotent — no error if already added."""
    device = await Device.get(id=device_id)
    tag = await Tag.get(id=tag_id)
    # Tortoise M2M .add() is idempotent when the relationship already exists
    await device.tags.add(tag)


async def remove_tag_from_device(device_id: int, tag_id: int) -> None:
    """Remove a tag from a device. No-op if the tag isn't attached or doesn't exist."""
    device = await Device.get_or_none(id=device_id)
    if device is None:
        return
    tag = await Tag.get_or_none(id=tag_id)
    if tag is None:
        return
    await device.tags.remove(tag)


async def get_devices_by_tag(tag_name: str) -> list[Device]:
    """Get all devices that have the given tag name."""
    tag = await Tag.get_or_none(name=tag_name)
    if tag is None:
        return []
    return await tag.devices.all()
