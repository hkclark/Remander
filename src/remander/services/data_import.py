"""Data import service — validates, migrates, and restores export data.

Format version migrations
─────────────────────────
When the export format changes (e.g. a new table is added), bump
CURRENT_FORMAT_VERSION and add a function to _MIGRATIONS keyed by the *old*
version number.  Each function receives the raw dict and must return an
upgraded dict.  Migrations run sequentially, so a v1 file on a v3 system
applies v1→v2 then v2→v3.

Example — when migration 10 adds a "schedules" table:

    def _upgrade_v1_to_v2(data: dict) -> dict:
        data.setdefault("schedules", [])
        return data

    _MIGRATIONS: dict[int, Callable[[dict], dict]] = {1: _upgrade_v1_to_v2}
    CURRENT_FORMAT_VERSION = 2
"""

from collections.abc import Callable

import attrs
from tortoise.transactions import in_transaction

from remander.models.app_config import AppConfig
from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask, ZoneMask
from remander.models.dashboard_button import DashboardButton
from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
from remander.models.detection import DeviceDetectionType
from remander.models.device import Device
from remander.models.plugin_data import PluginData
from remander.models.state import AppState
from remander.models.tag import Tag
from remander.models.user import User

# IMPORTANT — must be kept in sync with data_export.CURRENT_FORMAT_VERSION.
# Bump this whenever an aerich migration adds, removes, or renames a table that
# is included in the export.  See the module docstring above for the full
# checklist and a worked example.
CURRENT_FORMAT_VERSION = 1

# ── Format migrations ──────────────────────────────────────────────────────────
# Add entries here whenever CURRENT_FORMAT_VERSION is bumped.
# Key = the OLD version number that a given function upgrades FROM.

_MIGRATIONS: dict[int, Callable[[dict], dict]] = {}

_EMPTY_COLLECTIONS: dict[str, list] = {
    "hour_bitmasks": [],
    "zone_masks": [],
    "tags": [],
    "devices": [],
    "device_tags": [],
    "device_detection_types": [],
    "device_bitmask_assignments": [],
    "dashboard_buttons": [],
    "dashboard_button_bitmask_rules": [],
    "app_config": [],
    "plugin_data": [],
    "app_state": [],
    "users": [],
}


def migrate_to_current_format(data: dict) -> dict:
    """Apply sequential format migrations and fill any missing collection keys."""
    version = data.get("export_format_version", 0)
    for v in range(version, CURRENT_FORMAT_VERSION):
        fn = _MIGRATIONS.get(v)
        if fn:
            data = fn(data)
    # Ensure all collections exist (handles exports from older schema versions
    # that didn't include a table yet, and future exports with extra keys).
    for key, default in _EMPTY_COLLECTIONS.items():
        data.setdefault(key, list(default))
    data["export_format_version"] = CURRENT_FORMAT_VERSION
    return data


# ── Result types ───────────────────────────────────────────────────────────────


@attrs.define
class ImportCounts:
    hour_bitmask_count: int = 0
    zone_mask_count: int = 0
    tag_count: int = 0
    device_count: int = 0
    device_tag_count: int = 0
    device_detection_type_count: int = 0
    device_bitmask_assignment_count: int = 0
    dashboard_button_count: int = 0
    dashboard_button_rule_count: int = 0
    app_config_count: int = 0
    plugin_data_count: int = 0
    user_count: int = 0


@attrs.define
class ImportResult:
    success: bool
    counts: ImportCounts
    error: str | None = None


# ── Main import entry points ───────────────────────────────────────────────────


def preview_import(data: dict) -> ImportCounts:
    """Return record counts from an export dict without touching the database."""
    data = migrate_to_current_format(data)
    return ImportCounts(
        hour_bitmask_count=len(data["hour_bitmasks"]),
        zone_mask_count=len(data["zone_masks"]),
        tag_count=len(data["tags"]),
        device_count=len(data["devices"]),
        device_tag_count=len(data["device_tags"]),
        device_detection_type_count=len(data["device_detection_types"]),
        device_bitmask_assignment_count=len(data["device_bitmask_assignments"]),
        dashboard_button_count=len(data["dashboard_buttons"]),
        dashboard_button_rule_count=len(data["dashboard_button_bitmask_rules"]),
        app_config_count=len(data["app_config"]),
        plugin_data_count=len(data["plugin_data"]),
        user_count=len(data["users"]),
    )


async def apply_import(data: dict) -> ImportResult:
    """Wipe all application data and restore from the export dict.

    Runs inside a single transaction — if anything fails the database is
    left unchanged.
    """
    data = migrate_to_current_format(data)
    counts = ImportCounts()
    try:
        async with in_transaction():
            await _wipe_all()
            counts.hour_bitmask_count = await _restore_hour_bitmasks(data["hour_bitmasks"])
            counts.zone_mask_count = await _restore_zone_masks(data["zone_masks"])
            counts.tag_count = await _restore_tags(data["tags"])
            counts.device_count = await _restore_devices(data["devices"])
            counts.device_tag_count = await _restore_device_tags(data["device_tags"])
            counts.device_detection_type_count = await _restore_device_detection_types(
                data["device_detection_types"]
            )
            counts.device_bitmask_assignment_count = await _restore_device_bitmask_assignments(
                data["device_bitmask_assignments"]
            )
            counts.dashboard_button_count = await _restore_dashboard_buttons(
                data["dashboard_buttons"]
            )
            counts.dashboard_button_rule_count = await _restore_dashboard_button_rules(
                data["dashboard_button_bitmask_rules"]
            )
            counts.app_config_count = await _restore_app_config(data["app_config"])
            await _restore_plugin_data(data["plugin_data"])
            await _restore_app_state(data["app_state"])
            counts.user_count = await _restore_users(data["users"])
    except Exception as exc:
        return ImportResult(success=False, counts=counts, error=str(exc))
    return ImportResult(success=True, counts=counts)


# ── Wipe helpers ───────────────────────────────────────────────────────────────


async def _wipe_all() -> None:
    """Delete all application data in reverse dependency order."""
    await DashboardButtonBitmaskRule.all().delete()
    await DeviceBitmaskAssignment.all().delete()
    await DeviceDetectionType.all().delete()
    # Clear M2M device_tag junction by clearing all devices' tags
    for dev in await Device.all().prefetch_related("tags"):
        await dev.tags.clear()
    await DashboardButton.all().delete()
    await Device.all().delete()
    await Tag.all().delete()
    await HourBitmask.all().delete()
    await ZoneMask.all().delete()
    await AppConfig.all().delete()
    await PluginData.all().delete()
    await AppState.all().delete()
    await User.all().delete()


# ── Restore helpers ────────────────────────────────────────────────────────────


async def _restore_hour_bitmasks(rows: list[dict]) -> int:
    for row in rows:
        await HourBitmask.create(**row)
    return len(rows)


async def _restore_zone_masks(rows: list[dict]) -> int:
    for row in rows:
        await ZoneMask.create(**row)
    return len(rows)


async def _restore_tags(rows: list[dict]) -> int:
    for row in rows:
        await Tag.create(**row)
    return len(rows)


async def _restore_devices(rows: list[dict]) -> int:
    """Two-pass restore: create all devices first, then wire power_device refs."""
    # Pass 1: create devices without power_device
    for row in rows:
        data = {k: v for k, v in row.items() if k != "power_device_name"}
        await Device.create(**data)

    # Pass 2: set power_device foreign keys by name
    for row in rows:
        power_name = row.get("power_device_name")
        if power_name:
            dev = await Device.get(name=row["name"])
            power_dev = await Device.get_or_none(name=power_name)
            if power_dev:
                dev.power_device = power_dev
                await dev.save()

    return len(rows)


async def _restore_device_tags(rows: list[dict]) -> int:
    count = 0
    for row in rows:
        dev = await Device.get_or_none(name=row["device_name"])
        tag = await Tag.get_or_none(name=row["tag_name"])
        if dev and tag:
            await dev.tags.add(tag)
            count += 1
    return count


async def _restore_device_detection_types(rows: list[dict]) -> int:
    count = 0
    for row in rows:
        dev = await Device.get_or_none(name=row["device_name"])
        if dev:
            await DeviceDetectionType.create(
                device=dev,
                detection_type=row["detection_type"],
                is_enabled=row["is_enabled"],
            )
            count += 1
    return count


async def _restore_device_bitmask_assignments(rows: list[dict]) -> int:
    count = 0
    for row in rows:
        dev = await Device.get_or_none(name=row["device_name"])
        if not dev:
            continue
        bitmask = await HourBitmask.get_or_none(name=row["hour_bitmask_name"]) if row["hour_bitmask_name"] else None
        zone = await ZoneMask.get_or_none(name=row["zone_mask_name"]) if row["zone_mask_name"] else None
        await DeviceBitmaskAssignment.create(
            device=dev,
            mode=row["mode"],
            detection_type=row["detection_type"],
            hour_bitmask=bitmask,
            zone_mask=zone,
        )
        count += 1
    return count


async def _restore_dashboard_buttons(rows: list[dict]) -> int:
    for row in rows:
        await DashboardButton.create(**row)
    return len(rows)


async def _restore_dashboard_button_rules(rows: list[dict]) -> int:
    count = 0
    for row in rows:
        btn = await DashboardButton.get_or_none(name=row["dashboard_button_name"])
        tag = await Tag.get_or_none(name=row["tag_name"])
        bitmask = await HourBitmask.get_or_none(name=row["hour_bitmask_name"])
        if btn and tag and bitmask:
            await DashboardButtonBitmaskRule.create(
                dashboard_button=btn, tag=tag, hour_bitmask=bitmask
            )
            count += 1
    return count


async def _restore_app_config(rows: list[dict]) -> int:
    for row in rows:
        await AppConfig.create(key=row["key"], value=row["value"])
    return len(rows)


async def _restore_plugin_data(rows: list[dict]) -> None:
    for row in rows:
        await PluginData.create(
            plugin_name=row["plugin_name"], key=row["key"], value=row["value"]
        )


async def _restore_app_state(rows: list[dict]) -> None:
    for row in rows:
        await AppState.create(key=row["key"], value=row["value"])


async def _restore_users(rows: list[dict]) -> int:
    for row in rows:
        await User.create(**row)
    return len(rows)
