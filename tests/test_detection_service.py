"""Tests for the detection type service — RED phase (TDD)."""

from remander.models.detection import DeviceDetectionType
from remander.models.enums import DetectionType
from remander.services.detection import (
    disable_detection_type,
    enable_detection_type,
    get_enabled_detection_types,
    set_detection_types,
)
from tests.factories import create_camera


class TestSetDetectionTypes:
    async def test_set_detection_types(self) -> None:
        camera = await create_camera(name="Detection Cam")
        await set_detection_types(
            camera.id, [DetectionType.MOTION, DetectionType.PERSON, DetectionType.VEHICLE]
        )

        types = await DeviceDetectionType.filter(device_id=camera.id)
        assert len(types) == 3
        type_set = {t.detection_type for t in types}
        assert type_set == {DetectionType.MOTION, DetectionType.PERSON, DetectionType.VEHICLE}

    async def test_set_detection_types_replaces_existing(self) -> None:
        camera = await create_camera(name="Replace Cam")
        await set_detection_types(camera.id, [DetectionType.MOTION, DetectionType.PERSON])
        await set_detection_types(camera.id, [DetectionType.VEHICLE, DetectionType.ANIMAL])

        types = await DeviceDetectionType.filter(device_id=camera.id)
        assert len(types) == 2
        type_set = {t.detection_type for t in types}
        assert type_set == {DetectionType.VEHICLE, DetectionType.ANIMAL}

    async def test_set_empty_detection_types_clears_all(self) -> None:
        camera = await create_camera(name="Clear Cam")
        await set_detection_types(camera.id, [DetectionType.MOTION])
        await set_detection_types(camera.id, [])

        types = await DeviceDetectionType.filter(device_id=camera.id)
        assert len(types) == 0


class TestEnableDetectionType:
    async def test_enable_existing_disabled_type(self) -> None:
        camera = await create_camera(name="Enable Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.PERSON, is_enabled=False
        )

        await enable_detection_type(camera.id, DetectionType.PERSON)

        dt = await DeviceDetectionType.get(device_id=camera.id, detection_type=DetectionType.PERSON)
        assert dt.is_enabled is True

    async def test_enable_already_enabled_is_no_op(self) -> None:
        camera = await create_camera(name="Already Enabled Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )

        await enable_detection_type(camera.id, DetectionType.MOTION)

        dt = await DeviceDetectionType.get(device_id=camera.id, detection_type=DetectionType.MOTION)
        assert dt.is_enabled is True


class TestDisableDetectionType:
    async def test_disable_existing_enabled_type(self) -> None:
        camera = await create_camera(name="Disable Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.VEHICLE, is_enabled=True
        )

        await disable_detection_type(camera.id, DetectionType.VEHICLE)

        dt = await DeviceDetectionType.get(
            device_id=camera.id, detection_type=DetectionType.VEHICLE
        )
        assert dt.is_enabled is False

    async def test_disable_already_disabled_is_no_op(self) -> None:
        camera = await create_camera(name="Already Off Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.ANIMAL, is_enabled=False
        )

        await disable_detection_type(camera.id, DetectionType.ANIMAL)

        dt = await DeviceDetectionType.get(device_id=camera.id, detection_type=DetectionType.ANIMAL)
        assert dt.is_enabled is False


class TestGetEnabledDetectionTypes:
    async def test_get_enabled_detection_types(self) -> None:
        camera = await create_camera(name="Mixed Cam")
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.PERSON, is_enabled=True
        )
        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.VEHICLE, is_enabled=False
        )

        enabled = await get_enabled_detection_types(camera.id)
        assert len(enabled) == 2
        type_set = {dt.detection_type for dt in enabled}
        assert type_set == {DetectionType.MOTION, DetectionType.PERSON}

    async def test_get_enabled_when_none(self) -> None:
        camera = await create_camera(name="No Detection Cam")
        enabled = await get_enabled_detection_types(camera.id)
        assert enabled == []
