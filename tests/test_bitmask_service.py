"""Tests for the bitmask service — RED phase (TDD)."""

import pytest

from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask, ZoneMask
from remander.models.enums import DetectionType, HourBitmaskSubtype, Mode
from remander.services.bitmask import (
    assign_bitmask,
    create_hour_bitmask,
    create_zone_mask,
    delete_assignment,
    delete_hour_bitmask,
    delete_zone_mask,
    get_assignments_for_device,
    get_hour_bitmask,
    get_zone_mask,
    list_hour_bitmasks,
    list_zone_masks,
    resolve_bitmasks_for_device,
    resolve_hour_bitmask,
    update_hour_bitmask,
    update_zone_mask,
)
from tests.factories import (
    create_camera,
    create_dynamic_hour_bitmask,
)
from tests.factories import (
    create_hour_bitmask as factory_hour_bitmask,
)
from tests.factories import (
    create_zone_mask as factory_zone_mask,
)

# --- Hour Bitmask CRUD ---


class TestCreateHourBitmask:
    async def test_create_static(self) -> None:
        bm = await create_hour_bitmask(
            name="All Day",
            subtype=HourBitmaskSubtype.STATIC,
            static_value="1" * 24,
        )
        assert bm.id is not None
        assert bm.name == "All Day"
        assert bm.subtype == HourBitmaskSubtype.STATIC
        assert bm.static_value == "1" * 24

    async def test_create_dynamic(self) -> None:
        bm = await create_hour_bitmask(
            name="Sunrise Dynamic",
            subtype=HourBitmaskSubtype.DYNAMIC,
            sunrise_offset_minutes=30,
            sunset_offset_minutes=-30,
            fill_value="1",
        )
        assert bm.subtype == HourBitmaskSubtype.DYNAMIC
        assert bm.sunrise_offset_minutes == 30
        assert bm.sunset_offset_minutes == -30
        assert bm.fill_value == "1"

    async def test_create_invalid_static_value_too_short(self) -> None:
        with pytest.raises(ValueError, match="24"):
            await create_hour_bitmask(
                name="Bad",
                subtype=HourBitmaskSubtype.STATIC,
                static_value="111",
            )

    async def test_create_invalid_static_value_bad_chars(self) -> None:
        with pytest.raises(ValueError, match="0.*1"):
            await create_hour_bitmask(
                name="Bad Chars",
                subtype=HourBitmaskSubtype.STATIC,
                static_value="abcdefghijklmnopqrstuvwx",
            )

    async def test_create_duplicate_name_fails(self) -> None:
        await create_hour_bitmask(
            name="Unique", subtype=HourBitmaskSubtype.STATIC, static_value="0" * 24
        )
        with pytest.raises(Exception):
            await create_hour_bitmask(
                name="Unique", subtype=HourBitmaskSubtype.STATIC, static_value="0" * 24
            )


class TestGetHourBitmask:
    async def test_get_existing(self) -> None:
        created = await factory_hour_bitmask(name="Get Test")
        fetched = await get_hour_bitmask(created.id)
        assert fetched is not None
        assert fetched.name == "Get Test"

    async def test_get_nonexistent(self) -> None:
        result = await get_hour_bitmask(99999)
        assert result is None


class TestListHourBitmasks:
    async def test_list_all(self) -> None:
        await factory_hour_bitmask(name="BM 1")
        await factory_hour_bitmask(name="BM 2")
        result = await list_hour_bitmasks()
        assert len(result) == 2

    async def test_list_empty(self) -> None:
        result = await list_hour_bitmasks()
        assert result == []


class TestUpdateHourBitmask:
    async def test_update_name(self) -> None:
        bm = await factory_hour_bitmask(name="Old Name")
        updated = await update_hour_bitmask(bm.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    async def test_update_nonexistent(self) -> None:
        result = await update_hour_bitmask(99999, name="Nope")
        assert result is None

    async def test_update_static_value_validated(self) -> None:
        bm = await factory_hour_bitmask(name="Validate Update")
        with pytest.raises(ValueError, match="24"):
            await update_hour_bitmask(bm.id, static_value="111")


class TestDeleteHourBitmask:
    async def test_delete(self) -> None:
        bm = await factory_hour_bitmask(name="Doomed")
        assert await delete_hour_bitmask(bm.id) is True
        assert await HourBitmask.get_or_none(id=bm.id) is None

    async def test_delete_nonexistent(self) -> None:
        assert await delete_hour_bitmask(99999) is False


# --- Zone Mask CRUD ---


class TestCreateZoneMask:
    async def test_create(self) -> None:
        zm = await create_zone_mask(name="Full Frame", mask_value="1" * 4800)
        assert zm.id is not None
        assert zm.name == "Full Frame"
        assert len(zm.mask_value) == 4800

    async def test_create_invalid_length(self) -> None:
        with pytest.raises(ValueError, match="4800"):
            await create_zone_mask(name="Bad", mask_value="111")

    async def test_create_invalid_chars(self) -> None:
        with pytest.raises(ValueError, match="0.*1"):
            await create_zone_mask(name="Bad Chars", mask_value="x" * 4800)


class TestGetZoneMask:
    async def test_get_existing(self) -> None:
        created = await factory_zone_mask(name="Get ZM")
        fetched = await get_zone_mask(created.id)
        assert fetched is not None
        assert fetched.name == "Get ZM"

    async def test_get_nonexistent(self) -> None:
        assert await get_zone_mask(99999) is None


class TestListZoneMasks:
    async def test_list_all(self) -> None:
        await factory_zone_mask(name="ZM 1")
        await factory_zone_mask(name="ZM 2")
        result = await list_zone_masks()
        assert len(result) == 2


class TestUpdateZoneMask:
    async def test_update(self) -> None:
        zm = await factory_zone_mask(name="Old ZM")
        updated = await update_zone_mask(zm.id, name="New ZM")
        assert updated is not None
        assert updated.name == "New ZM"

    async def test_update_nonexistent(self) -> None:
        assert await update_zone_mask(99999, name="Nope") is None

    async def test_update_mask_value_validated(self) -> None:
        zm = await factory_zone_mask(name="Validate ZM")
        with pytest.raises(ValueError, match="4800"):
            await update_zone_mask(zm.id, mask_value="111")


class TestDeleteZoneMask:
    async def test_delete(self) -> None:
        zm = await factory_zone_mask(name="Doomed ZM")
        assert await delete_zone_mask(zm.id) is True
        assert await ZoneMask.get_or_none(id=zm.id) is None

    async def test_delete_nonexistent(self) -> None:
        assert await delete_zone_mask(99999) is False


# --- Bitmask Assignment CRUD ---


class TestAssignBitmask:
    async def test_create_assignment(self) -> None:
        camera = await create_camera(name="Assign Cam")
        hb = await factory_hour_bitmask(name="Assign HB")
        zm = await factory_zone_mask(name="Assign ZM")

        assignment = await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb.id,
            zone_mask_id=zm.id,
        )
        assert assignment.id is not None
        assert assignment.device_id == camera.id
        assert assignment.mode == Mode.AWAY
        assert assignment.detection_type == DetectionType.MOTION

    async def test_upsert_existing_assignment(self) -> None:
        """Assigning the same device+mode+detection_type should update, not duplicate."""
        camera = await create_camera(name="Upsert Cam")
        hb1 = await factory_hour_bitmask(name="HB First")
        hb2 = await factory_hour_bitmask(name="HB Second")

        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb1.id,
        )
        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb2.id,
        )

        assignments = await DeviceBitmaskAssignment.filter(device_id=camera.id)
        assert len(assignments) == 1
        assert assignments[0].hour_bitmask_id == hb2.id

    async def test_assign_with_null_bitmasks(self) -> None:
        camera = await create_camera(name="Null Cam")
        assignment = await assign_bitmask(
            device_id=camera.id,
            mode=Mode.HOME,
            detection_type=DetectionType.PERSON,
        )
        assert assignment.hour_bitmask_id is None
        assert assignment.zone_mask_id is None


class TestGetAssignmentsForDevice:
    async def test_get_all_assignments(self) -> None:
        camera = await create_camera(name="Multi Cam")
        hb = await factory_hour_bitmask(name="Multi HB")

        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb.id,
        )
        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.HOME,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb.id,
        )

        all_assignments = await get_assignments_for_device(camera.id)
        assert len(all_assignments) == 2

    async def test_filter_by_mode(self) -> None:
        camera = await create_camera(name="Filter Cam")
        hb = await factory_hour_bitmask(name="Filter HB")

        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb.id,
        )
        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.HOME,
            detection_type=DetectionType.PERSON,
            hour_bitmask_id=hb.id,
        )

        away_only = await get_assignments_for_device(camera.id, mode=Mode.AWAY)
        assert len(away_only) == 1
        assert away_only[0].mode == Mode.AWAY


class TestDeleteAssignment:
    async def test_delete(self) -> None:
        camera = await create_camera(name="Del Assign Cam")
        assignment = await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
        )
        assert await delete_assignment(assignment.id) is True
        assert await DeviceBitmaskAssignment.get_or_none(id=assignment.id) is None

    async def test_delete_nonexistent(self) -> None:
        assert await delete_assignment(99999) is False


# --- Bitmask Resolution ---


class TestResolveHourBitmask:
    async def test_resolve_static(self) -> None:
        bm = await factory_hour_bitmask(
            name="Static Resolve",
            static_value="000000111111111111110000",
        )
        result = await resolve_hour_bitmask(bm)
        assert result == "000000111111111111110000"

    async def test_resolve_dynamic(self) -> None:
        """Dynamic bitmask should compute from sunrise/sunset."""
        bm = await create_dynamic_hour_bitmask(
            name="Dynamic Resolve",
            sunrise_offset_minutes=0,
            sunset_offset_minutes=0,
            fill_value="1",
        )
        # The result depends on location and date; just verify it's a valid 24-char bitmask
        result = await resolve_hour_bitmask(bm, latitude=40.7128, longitude=-74.0060)
        assert len(result) == 24
        assert all(c in "01" for c in result)


class TestResolveBitmasksForDevice:
    async def test_resolve_with_assignments(self) -> None:
        # zone_masks_enabled=True and zone_mask_away set: zone_value comes from the device
        camera = await create_camera(
            name="Resolve Cam", zone_masks_enabled=True, zone_mask_away="1" * 4800
        )
        hb = await factory_hour_bitmask(name="Resolve HB", static_value="000000111111111111110000")

        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )
        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=hb.id,
        )

        result = await resolve_bitmasks_for_device(camera.id, Mode.AWAY)
        assert len(result) == 1
        assert result[0]["detection_type"] == DetectionType.MOTION
        assert result[0]["hour_bitmask"] == "000000111111111111110000"
        assert result[0]["zone_mask"] == "1" * 4800

    async def test_resolve_no_assignment_uses_zeros(self) -> None:
        """When no assignment exists for an enabled detection type, use all zeros for hour bitmask.
        Zone mask is None when zone_masks_enabled=False (the default)."""
        camera = await create_camera(name="Zero Cam")
        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.PERSON, is_enabled=True
        )

        result = await resolve_bitmasks_for_device(camera.id, Mode.AWAY)
        assert len(result) == 1
        assert result[0]["detection_type"] == DetectionType.PERSON
        assert result[0]["hour_bitmask"] == "0" * 24
        assert result[0]["zone_mask"] is None

    async def test_resolve_disabled_detection_type_excluded(self) -> None:
        """Disabled detection types should not appear in resolution."""
        camera = await create_camera(name="Disabled DT Cam")
        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=False
        )

        result = await resolve_bitmasks_for_device(camera.id, Mode.AWAY)
        assert len(result) == 0

    async def test_resolve_null_bitmask_in_assignment_uses_zeros(self) -> None:
        """Assignment with null hour_bitmask → all-zero hour bitmask.
        Zone mask is None when zone_masks_enabled=False (the default)."""
        camera = await create_camera(name="Null HB Cam")
        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )
        await assign_bitmask(
            device_id=camera.id,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask_id=None,
            zone_mask_id=None,
        )

        result = await resolve_bitmasks_for_device(camera.id, Mode.AWAY)
        assert result[0]["hour_bitmask"] == "0" * 24
        assert result[0]["zone_mask"] is None
