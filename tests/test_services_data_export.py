"""Tests for the data export service."""

import pytest

from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask, ZoneMask
from remander.models.detection import DeviceDetectionType
from remander.models.enums import DetectionType, HourBitmaskSubtype, Mode
from remander.services.data_export import CURRENT_FORMAT_VERSION, export_data
from tests.factories import create_camera, create_power_device, create_tag


class TestExportStructure:
    async def test_export_format_version(self) -> None:
        data = await export_data()
        assert data["export_format_version"] == CURRENT_FORMAT_VERSION

    async def test_export_has_exported_at(self) -> None:
        data = await export_data()
        assert "exported_at" in data
        assert data["exported_at"]  # non-empty string

    async def test_export_includes_all_collections(self) -> None:
        data = await export_data()
        expected = [
            "hour_bitmasks",
            "zone_masks",
            "tags",
            "devices",
            "device_tags",
            "device_detection_types",
            "device_bitmask_assignments",
            "dashboard_buttons",
            "dashboard_button_bitmask_rules",
            "app_config",
            "plugin_data",
            "app_state",
            "users",
        ]
        for key in expected:
            assert key in data, f"Missing collection: {key!r}"

    async def test_export_empty_db_has_empty_lists(self) -> None:
        data = await export_data()
        assert data["devices"] == []
        assert data["tags"] == []
        assert data["hour_bitmasks"] == []


class TestExportDevices:
    async def test_device_fields_present(self) -> None:
        await create_camera(name="Front Cam", channel=1)
        data = await export_data()
        dev = data["devices"][0]
        assert dev["name"] == "Front Cam"
        assert dev["channel"] == 1
        assert "device_type" in dev
        assert "brand" in dev

    async def test_power_device_exported_as_name(self) -> None:
        switch = await create_power_device(name="Hallway Switch")
        cam = await create_camera(name="Hall Cam")
        cam.power_device_id = switch.id
        await cam.save()

        data = await export_data()
        cam_data = next(d for d in data["devices"] if d["name"] == "Hall Cam")
        assert cam_data["power_device_name"] == "Hallway Switch"

    async def test_no_power_device_exports_null(self) -> None:
        await create_camera(name="Lone Cam")
        data = await export_data()
        cam_data = next(d for d in data["devices"] if d["name"] == "Lone Cam")
        assert cam_data["power_device_name"] is None

    async def test_no_numeric_ids_in_device_export(self) -> None:
        await create_camera(name="Id Cam")
        data = await export_data()
        dev = next(d for d in data["devices"] if d["name"] == "Id Cam")
        assert "id" not in dev
        assert "power_device_id" not in dev


class TestExportRelationships:
    async def test_device_tags_exported_by_name(self) -> None:
        cam = await create_camera(name="Tagged Cam")
        tag = await create_tag(name="outdoor")
        await cam.tags.add(tag)

        data = await export_data()
        assert {"device_name": "Tagged Cam", "tag_name": "outdoor"} in data["device_tags"]

    async def test_device_detection_types_exported_by_device_name(self) -> None:
        cam = await create_camera(name="AI Cam")
        await DeviceDetectionType.create(
            device=cam, detection_type=DetectionType.PERSON, is_enabled=True
        )
        data = await export_data()
        dt = next(
            d for d in data["device_detection_types"] if d["device_name"] == "AI Cam"
        )
        assert dt["detection_type"] == DetectionType.PERSON
        assert dt["is_enabled"] is True

    async def test_bitmask_assignments_exported_by_names(self) -> None:
        cam = await create_camera(name="Schedule Cam")
        bitmask = await HourBitmask.create(
            name="All Day",
            subtype=HourBitmaskSubtype.STATIC,
            static_value="1" * 24,
        )
        await DeviceBitmaskAssignment.create(
            device=cam,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask=bitmask,
            zone_mask=None,
        )
        data = await export_data()
        asgn = next(
            d for d in data["device_bitmask_assignments"] if d["device_name"] == "Schedule Cam"
        )
        assert asgn["hour_bitmask_name"] == "All Day"
        assert asgn["zone_mask_name"] is None
        assert "hour_bitmask_id" not in asgn
