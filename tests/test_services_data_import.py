"""Tests for the data import service."""

import pytest

from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask, ZoneMask
from remander.models.detection import DeviceDetectionType
from remander.models.device import Device
from remander.models.enums import DetectionType, HourBitmaskSubtype, Mode
from remander.models.tag import Tag
from remander.models.user import User
from remander.services.data_export import export_data
from remander.services.data_import import (
    CURRENT_FORMAT_VERSION,
    apply_import,
    migrate_to_current_format,
)
from tests.factories import create_camera, create_power_device, create_tag, create_user


class TestMigrateToCurrentFormat:
    def test_noop_on_current_version(self) -> None:
        data = {"export_format_version": CURRENT_FORMAT_VERSION, "tags": [{"name": "x"}]}
        result = migrate_to_current_format(data)
        assert result["export_format_version"] == CURRENT_FORMAT_VERSION
        assert result["tags"] == [{"name": "x"}]

    def test_fills_in_missing_collections_with_empty_lists(self) -> None:
        data = {"export_format_version": CURRENT_FORMAT_VERSION}
        result = migrate_to_current_format(data)
        for key in ["hour_bitmasks", "zone_masks", "tags", "devices", "device_tags",
                    "device_detection_types", "device_bitmask_assignments",
                    "dashboard_buttons", "dashboard_button_bitmask_rules",
                    "app_config", "plugin_data", "app_state", "users"]:
            assert key in result, f"Missing default for {key!r}"
            assert isinstance(result[key], list)


class TestApplyImport:
    async def test_round_trip_tags(self) -> None:
        await create_tag(name="outdoor", color="sky", show_on_dashboard=True)
        data = await export_data()
        await Tag.all().delete()

        result = await apply_import(data)
        assert result.success
        tag = await Tag.get(name="outdoor")
        assert tag.color == "sky"
        assert tag.show_on_dashboard is True

    async def test_round_trip_devices(self) -> None:
        await create_camera(name="Front Cam", channel=3)
        data = await export_data()
        await Device.all().delete()

        await apply_import(data)
        cam = await Device.get(name="Front Cam")
        assert cam.channel == 3

    async def test_round_trip_power_device_reference(self) -> None:
        switch = await create_power_device(name="Switch")
        cam = await create_camera(name="Cam With Power")
        cam.power_device_id = switch.id
        await cam.save()

        data = await export_data()
        await Device.all().delete()

        await apply_import(data)
        cam = await Device.get(name="Cam With Power")
        await cam.fetch_related("power_device")
        assert cam.power_device is not None
        assert cam.power_device.name == "Switch"

    async def test_round_trip_device_tags(self) -> None:
        cam = await create_camera(name="Tag Cam")
        tag = await create_tag(name="indoor")
        await cam.tags.add(tag)

        data = await export_data()
        await Device.all().delete()
        await Tag.all().delete()

        await apply_import(data)
        restored_cam = await Device.get(name="Tag Cam")
        await restored_cam.fetch_related("tags")
        assert any(t.name == "indoor" for t in restored_cam.tags)

    async def test_round_trip_hour_bitmask(self) -> None:
        await HourBitmask.create(
            name="Night Only",
            subtype=HourBitmaskSubtype.STATIC,
            static_value="0" * 8 + "1" * 8 + "0" * 8,
        )
        data = await export_data()
        await HourBitmask.all().delete()

        await apply_import(data)
        bm = await HourBitmask.get(name="Night Only")
        assert bm.subtype == HourBitmaskSubtype.STATIC

    async def test_round_trip_users(self) -> None:
        await create_user(email="admin@home.local", is_admin=True)
        data = await export_data()
        await User.all().delete()

        await apply_import(data)
        user = await User.get(email="admin@home.local")
        assert user.is_admin is True

    async def test_import_wipes_existing_data(self) -> None:
        original = await create_tag(name="original")
        data = await export_data()

        # Add a new tag that is NOT in the export
        await create_tag(name="stale-tag")

        await apply_import(data)
        tags = await Tag.all()
        names = {t.name for t in tags}
        assert "original" in names
        assert "stale-tag" not in names

    async def test_import_tolerates_missing_collections(self) -> None:
        # An export file that only has tags and nothing else
        data = {
            "export_format_version": CURRENT_FORMAT_VERSION,
            "exported_at": "2026-01-01T00:00:00Z",
            "tags": [{"name": "partial", "show_on_dashboard": False, "color": None}],
        }
        result = await apply_import(data)
        assert result.success
        tag = await Tag.get(name="partial")
        assert tag.name == "partial"

    async def test_import_result_contains_counts(self) -> None:
        await create_tag(name="t1")
        await create_camera(name="c1")
        data = await export_data()
        await Device.all().delete()
        await Tag.all().delete()

        result = await apply_import(data)
        assert result.counts.tag_count == 1
        assert result.counts.device_count == 1
