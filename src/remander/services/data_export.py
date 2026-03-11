"""Data export service — serialises all application data to a portable dict.

Cross-table references are stored as natural keys (names) rather than numeric
IDs so that the export is portable and human-readable.  Numeric IDs are
regenerated on import.
"""

from datetime import datetime, timezone

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

# IMPORTANT — bump this whenever an aerich migration adds, removes, or renames
# a table that is included in the export (i.e. any table serialised by a helper
# below).  Purely internal tables (activity logs, command history) don't need a
# bump.
#
# When bumping:
#   1. Increment CURRENT_FORMAT_VERSION here AND in data_import.py (they must match).
#   2. Add a migration function to data_import._MIGRATIONS keyed by the OLD version.
#   3. Update the export helper(s) below to include the new/changed data.
#
# See data_import.py module docstring for a worked example.
CURRENT_FORMAT_VERSION = 1


async def export_data() -> dict:
    """Collect all application data and return a portable export dict."""
    return {
        "export_format_version": CURRENT_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "hour_bitmasks": await _export_hour_bitmasks(),
        "zone_masks": await _export_zone_masks(),
        "tags": await _export_tags(),
        "devices": await _export_devices(),
        "device_tags": await _export_device_tags(),
        "device_detection_types": await _export_device_detection_types(),
        "device_bitmask_assignments": await _export_device_bitmask_assignments(),
        "dashboard_buttons": await _export_dashboard_buttons(),
        "dashboard_button_bitmask_rules": await _export_dashboard_button_bitmask_rules(),
        "app_config": await _export_app_config(),
        "plugin_data": await _export_plugin_data(),
        "app_state": await _export_app_state(),
        "users": await _export_users(),
    }


# ── Per-table helpers ──────────────────────────────────────────────────────────


async def _export_hour_bitmasks() -> list[dict]:
    rows = []
    for bm in await HourBitmask.all():
        rows.append(
            {
                "name": bm.name,
                "subtype": bm.subtype,
                "static_value": bm.static_value,
                "sunrise_offset_minutes": bm.sunrise_offset_minutes,
                "sunset_offset_minutes": bm.sunset_offset_minutes,
                "fill_value": bm.fill_value,
            }
        )
    return rows


async def _export_zone_masks() -> list[dict]:
    rows = []
    for zm in await ZoneMask.all():
        rows.append({"name": zm.name, "mask_value": zm.mask_value})
    return rows


async def _export_tags() -> list[dict]:
    rows = []
    for tag in await Tag.all():
        rows.append(
            {
                "name": tag.name,
                "show_on_dashboard": tag.show_on_dashboard,
                "color": tag.color,
            }
        )
    return rows


async def _export_devices() -> list[dict]:
    rows = []
    devices = await Device.all().prefetch_related("power_device")
    for dev in devices:
        rows.append(
            {
                "name": dev.name,
                "device_type": dev.device_type,
                "device_subtype": dev.device_subtype,
                "brand": dev.brand,
                "model_name": dev.model_name,
                "hw_version": dev.hw_version,
                "firmware": dev.firmware,
                "ip_address": dev.ip_address,
                "channel": dev.channel,
                "is_wireless": dev.is_wireless,
                "is_poe": dev.is_poe,
                "resolution": dev.resolution,
                "has_ptz": dev.has_ptz,
                "ptz_away_preset": dev.ptz_away_preset,
                "ptz_home_preset": dev.ptz_home_preset,
                "ptz_speed": dev.ptz_speed,
                "power_device_name": dev.power_device.name if dev.power_device else None,
                "zone_masks_enabled": dev.zone_masks_enabled,
                "zone_mask_away": dev.zone_mask_away,
                "zone_mask_home": dev.zone_mask_home,
                "notes": dev.notes,
                "is_enabled": dev.is_enabled,
            }
        )
    return rows


async def _export_device_tags() -> list[dict]:
    rows = []
    devices = await Device.all().prefetch_related("tags")
    for dev in devices:
        for tag in dev.tags:
            rows.append({"device_name": dev.name, "tag_name": tag.name})
    return rows


async def _export_device_detection_types() -> list[dict]:
    rows = []
    for ddt in await DeviceDetectionType.all().prefetch_related("device"):
        rows.append(
            {
                "device_name": ddt.device.name,
                "detection_type": ddt.detection_type,
                "is_enabled": ddt.is_enabled,
            }
        )
    return rows


async def _export_device_bitmask_assignments() -> list[dict]:
    rows = []
    for asgn in await DeviceBitmaskAssignment.all().prefetch_related(
        "device", "hour_bitmask", "zone_mask"
    ):
        rows.append(
            {
                "device_name": asgn.device.name,
                "mode": asgn.mode,
                "detection_type": asgn.detection_type,
                "hour_bitmask_name": asgn.hour_bitmask.name if asgn.hour_bitmask else None,
                "zone_mask_name": asgn.zone_mask.name if asgn.zone_mask else None,
            }
        )
    return rows


async def _export_dashboard_buttons() -> list[dict]:
    rows = []
    for btn in await DashboardButton.all():
        rows.append(
            {
                "name": btn.name,
                "color": btn.color,
                "delay_seconds": btn.delay_seconds,
                "operation_type": btn.operation_type,
                "sort_order": btn.sort_order,
                "is_enabled": btn.is_enabled,
                "show_on_main": btn.show_on_main,
                "show_on_guest": btn.show_on_guest,
            }
        )
    return rows


async def _export_dashboard_button_bitmask_rules() -> list[dict]:
    rows = []
    for rule in await DashboardButtonBitmaskRule.all().prefetch_related(
        "dashboard_button", "tag", "hour_bitmask"
    ):
        rows.append(
            {
                "dashboard_button_name": rule.dashboard_button.name,
                "tag_name": rule.tag.name,
                "hour_bitmask_name": rule.hour_bitmask.name,
            }
        )
    return rows


async def _export_app_config() -> list[dict]:
    rows = []
    for cfg in await AppConfig.all():
        rows.append({"key": cfg.key, "value": cfg.value})
    return rows


async def _export_plugin_data() -> list[dict]:
    rows = []
    for pd in await PluginData.all():
        rows.append({"plugin_name": pd.plugin_name, "key": pd.key, "value": pd.value})
    return rows


async def _export_app_state() -> list[dict]:
    rows = []
    for state in await AppState.all():
        rows.append({"key": state.key, "value": state.value})
    return rows


async def _export_users() -> list[dict]:
    rows = []
    for user in await User.all():
        rows.append(
            {
                "email": user.email,
                "display_name": user.display_name,
                "password_hash": user.password_hash,
                "token": user.token,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
            }
        )
    return rows
