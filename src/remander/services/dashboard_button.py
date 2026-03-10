"""DashboardButton service — CRUD and rule management for configurable dashboard action buttons."""

from remander.models.dashboard_button import DashboardButton
from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
from remander.models.device import Device
from remander.models.enums import ButtonColor, ButtonOperationType
from remander.models.tag import Tag


async def create_dashboard_button(
    name: str,
    operation_type: ButtonOperationType,
    *,
    color: ButtonColor = ButtonColor.BLUE,
    delay_seconds: int = 0,
    sort_order: int = 0,
    is_enabled: bool = True,
    show_on_main: bool = True,
    show_on_guest: bool = False,
) -> DashboardButton:
    """Create a new dashboard button."""
    return await DashboardButton.create(
        name=name,
        operation_type=operation_type,
        color=color,
        delay_seconds=delay_seconds,
        sort_order=sort_order,
        is_enabled=is_enabled,
        show_on_main=show_on_main,
        show_on_guest=show_on_guest,
    )


async def get_dashboard_button(button_id: int) -> DashboardButton | None:
    return await DashboardButton.get_or_none(id=button_id)


async def list_dashboard_buttons(
    *,
    enabled_only: bool = False,
    show_on_main: bool | None = None,
    show_on_guest: bool | None = None,
) -> list[DashboardButton]:
    qs = DashboardButton.all().order_by("sort_order", "id")
    if enabled_only:
        qs = qs.filter(is_enabled=True)
    if show_on_main is not None:
        qs = qs.filter(show_on_main=show_on_main)
    if show_on_guest is not None:
        qs = qs.filter(show_on_guest=show_on_guest)
    return await qs


async def update_dashboard_button(button_id: int, **kwargs: object) -> DashboardButton | None:
    btn = await DashboardButton.get_or_none(id=button_id)
    if btn is None:
        return None
    await btn.update_from_dict(kwargs).save()
    return btn


async def delete_dashboard_button(button_id: int) -> bool:
    btn = await DashboardButton.get_or_none(id=button_id)
    if btn is None:
        return False
    await btn.delete()
    return True


async def save_button_rules(button_id: int, rules: list[tuple[int, int]]) -> None:
    """Replace all tag-bitmask rules for a button.

    rules: list of (tag_id, hour_bitmask_id) pairs.
    Existing rules are deleted before new ones are created.
    """
    await DashboardButtonBitmaskRule.filter(dashboard_button_id=button_id).delete()
    for tag_id, bitmask_id in rules:
        await DashboardButtonBitmaskRule.create(
            dashboard_button_id=button_id,
            tag_id=tag_id,
            hour_bitmask_id=bitmask_id,
        )


async def list_rules_for_button(button_id: int) -> list[DashboardButtonBitmaskRule]:
    """Return all tag-bitmask rules for a button, with tag and hour_bitmask prefetched."""
    return await DashboardButtonBitmaskRule.filter(
        dashboard_button_id=button_id
    ).prefetch_related("tag", "hour_bitmask").all()


async def validate_button_rules(
    rules: list[tuple[int, int]],
) -> tuple[list[str], list[str]]:
    """Validate tag-bitmask rule pairs for a button.

    Returns (overlap_device_names, uncovered_device_names):
      - overlap_device_names: devices that appear in more than one tag in the rules (error)
      - uncovered_device_names: enabled devices not covered by any tag in the rules (warning)
    """
    # Build a map of tag_id -> set of device IDs in that tag
    tag_device_map: dict[int, set[int]] = {}
    for tag_id, _ in rules:
        tag = await Tag.get_or_none(id=tag_id)
        if tag is None:
            continue
        devices = await tag.devices.filter(is_enabled=True)
        tag_device_map[tag_id] = {d.id for d in devices}

    # Find devices that appear in more than one tag (overlap)
    seen: dict[int, int] = {}  # device_id -> first tag_id
    overlapping_device_ids: set[int] = set()
    for tag_id, device_ids in tag_device_map.items():
        for device_id in device_ids:
            if device_id in seen:
                overlapping_device_ids.add(device_id)
            else:
                seen[device_id] = tag_id

    overlap_device_names: list[str] = []
    for device_id in sorted(overlapping_device_ids):
        device = await Device.get_or_none(id=device_id)
        if device:
            overlap_device_names.append(device.name)

    # Find enabled devices not covered by any tag
    all_covered_ids: set[int] = set().union(*tag_device_map.values()) if tag_device_map else set()
    all_enabled_devices = await Device.filter(is_enabled=True)
    uncovered_device_names: list[str] = [
        d.name for d in all_enabled_devices if d.id not in all_covered_ids
    ]

    return overlap_device_names, uncovered_device_names
