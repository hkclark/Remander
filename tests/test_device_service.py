"""Tests for the device service — RED phase (TDD)."""

import pytest

from remander.models.device import Device
from remander.models.enums import DeviceBrand, DeviceType, PowerDeviceSubtype
from remander.services.device import (
    create_device,
    delete_device,
    get_cameras_with_power_devices,
    get_device,
    list_devices,
    set_power_device,
    update_device,
)
from tests.factories import create_camera, create_power_device, create_tag


class TestCreateDevice:
    async def test_create_camera(self) -> None:
        device = await create_device(
            name="Front Door Cam",
            device_type=DeviceType.CAMERA,
            brand=DeviceBrand.REOLINK,
            channel=0,
            ip_address="192.168.1.10",
        )
        assert device.id is not None
        assert device.name == "Front Door Cam"
        assert device.device_type == DeviceType.CAMERA
        assert device.brand == DeviceBrand.REOLINK
        assert device.channel == 0
        assert device.is_enabled is True

    async def test_create_power_device(self) -> None:
        device = await create_device(
            name="Garage Plug",
            device_type=DeviceType.POWER,
            brand=DeviceBrand.TAPO,
            device_subtype=PowerDeviceSubtype.SMART_PLUG,
            ip_address="192.168.1.200",
        )
        assert device.device_type == DeviceType.POWER
        assert device.brand == DeviceBrand.TAPO
        assert device.device_subtype == PowerDeviceSubtype.SMART_PLUG

    async def test_create_camera_with_ptz(self) -> None:
        device = await create_device(
            name="PTZ Cam",
            device_type=DeviceType.CAMERA,
            brand=DeviceBrand.REOLINK,
            has_ptz=True,
            ptz_away_preset=1,
            ptz_home_preset=2,
            ptz_speed=50,
        )
        assert device.has_ptz is True
        assert device.ptz_away_preset == 1
        assert device.ptz_home_preset == 2
        assert device.ptz_speed == 50

    async def test_create_device_duplicate_name_fails(self) -> None:
        await create_device(
            name="Unique Cam", device_type=DeviceType.CAMERA, brand=DeviceBrand.REOLINK
        )
        with pytest.raises(Exception):
            await create_device(
                name="Unique Cam", device_type=DeviceType.CAMERA, brand=DeviceBrand.REOLINK
            )


class TestGetDevice:
    async def test_get_existing_device(self) -> None:
        camera = await create_camera(name="Existing Cam", channel=1)
        device = await get_device(camera.id)
        assert device is not None
        assert device.name == "Existing Cam"
        assert device.channel == 1

    async def test_get_nonexistent_device_returns_none(self) -> None:
        device = await get_device(99999)
        assert device is None

    async def test_get_device_includes_tags(self) -> None:
        camera = await create_camera(name="Tagged Cam")
        tag = await create_tag(name="outdoor")
        await camera.tags.add(tag)

        device = await get_device(camera.id)
        assert device is not None
        tags = await device.tags.all()
        assert len(tags) == 1
        assert tags[0].name == "outdoor"

    async def test_get_device_includes_detection_types(self) -> None:
        from remander.models.detection import DeviceDetectionType
        from remander.models.enums import DetectionType

        camera = await create_camera(name="Detection Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.PERSON, is_enabled=True
        )

        device = await get_device(camera.id)
        assert device is not None
        detection_types = await device.detection_types.all()
        assert len(detection_types) == 1
        assert detection_types[0].detection_type == DetectionType.PERSON


class TestListDevices:
    async def test_list_all_devices(self) -> None:
        await create_camera(name="Cam 1")
        await create_camera(name="Cam 2")
        await create_power_device(name="Plug 1")

        devices = await list_devices()
        assert len(devices) == 3

    async def test_list_filter_by_device_type(self) -> None:
        await create_camera(name="Cam A")
        await create_power_device(name="Plug A")

        cameras = await list_devices(device_type=DeviceType.CAMERA)
        assert len(cameras) == 1
        assert cameras[0].device_type == DeviceType.CAMERA

        power_devices = await list_devices(device_type=DeviceType.POWER)
        assert len(power_devices) == 1
        assert power_devices[0].device_type == DeviceType.POWER

    async def test_list_filter_by_enabled(self) -> None:
        await create_camera(name="Enabled Cam", is_enabled=True)
        await create_camera(name="Disabled Cam", is_enabled=False)

        enabled = await list_devices(is_enabled=True)
        assert len(enabled) == 1
        assert enabled[0].name == "Enabled Cam"

        disabled = await list_devices(is_enabled=False)
        assert len(disabled) == 1
        assert disabled[0].name == "Disabled Cam"

    async def test_list_filter_combined(self) -> None:
        await create_camera(name="Active Cam", is_enabled=True)
        await create_camera(name="Inactive Cam", is_enabled=False)
        await create_power_device(name="Active Plug", is_enabled=True)

        result = await list_devices(device_type=DeviceType.CAMERA, is_enabled=True)
        assert len(result) == 1
        assert result[0].name == "Active Cam"

    async def test_list_empty(self) -> None:
        devices = await list_devices()
        assert devices == []


class TestUpdateDevice:
    async def test_update_device_fields(self) -> None:
        camera = await create_camera(name="Old Name", channel=0)
        updated = await update_device(camera.id, name="New Name", channel=5)
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.channel == 5

    async def test_update_nonexistent_device_returns_none(self) -> None:
        result = await update_device(99999, name="Nope")
        assert result is None

    async def test_update_persists_to_db(self) -> None:
        camera = await create_camera(name="Persist Test")
        await update_device(camera.id, notes="Updated notes")

        reloaded = await Device.get(id=camera.id)
        assert reloaded.notes == "Updated notes"


class TestDeleteDevice:
    async def test_delete_device(self) -> None:
        camera = await create_camera(name="Doomed Cam")
        result = await delete_device(camera.id)
        assert result is True

        deleted = await Device.get_or_none(id=camera.id)
        assert deleted is None

    async def test_delete_nonexistent_device_returns_false(self) -> None:
        result = await delete_device(99999)
        assert result is False

    async def test_delete_cascades_detection_types(self) -> None:
        from remander.models.detection import DeviceDetectionType
        from remander.models.enums import DetectionType

        camera = await create_camera(name="Cascade Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )
        await delete_device(camera.id)

        remaining = await DeviceDetectionType.filter(device_id=camera.id).count()
        assert remaining == 0

    async def test_delete_cascades_bitmask_assignments(self) -> None:
        from remander.models.bitmask import DeviceBitmaskAssignment
        from remander.models.enums import DetectionType, Mode

        camera = await create_camera(name="Bitmask Cam")
        await DeviceBitmaskAssignment.create(
            device=camera, mode=Mode.AWAY, detection_type=DetectionType.MOTION
        )
        await delete_device(camera.id)

        remaining = await DeviceBitmaskAssignment.filter(device_id=camera.id).count()
        assert remaining == 0


class TestSetPowerDevice:
    async def test_set_power_device(self) -> None:
        camera = await create_camera(name="Powered Cam")
        plug = await create_power_device(name="Camera Plug")

        result = await set_power_device(camera.id, plug.id)
        assert result is not None
        assert result.power_device_id == plug.id

    async def test_set_power_device_nonexistent_camera(self) -> None:
        plug = await create_power_device(name="Orphan Plug")
        result = await set_power_device(99999, plug.id)
        assert result is None

    async def test_clear_power_device(self) -> None:
        camera = await create_camera(name="Clear Cam")
        plug = await create_power_device(name="Temp Plug")
        await set_power_device(camera.id, plug.id)

        result = await set_power_device(camera.id, None)
        assert result is not None
        assert result.power_device_id is None


class TestGetCamerasWithPowerDevices:
    async def test_returns_cameras_with_power_devices(self) -> None:
        camera = await create_camera(name="Powered Cam")
        plug = await create_power_device(name="Its Plug")
        await set_power_device(camera.id, plug.id)

        # Camera without a power device — should not be in the results
        await create_camera(name="Unpowered Cam")

        cameras = await get_cameras_with_power_devices()
        assert len(cameras) == 1
        assert cameras[0].name == "Powered Cam"

    async def test_returns_empty_when_none(self) -> None:
        await create_camera(name="Solo Cam")
        cameras = await get_cameras_with_power_devices()
        assert cameras == []
