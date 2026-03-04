"""Tests for device operation workflow nodes — RED phase (TDD)."""

from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_graph import GraphRunContext

from remander.models.enums import (
    CommandType,
    DetectionType,
    Mode,
)
from remander.models.state import SavedDeviceState
from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode, SetZoneMasksNode
from remander.workflows.nodes.power import PowerOffNode, PowerOnNode, WaitForPowerOnNode
from remander.workflows.nodes.ptz import PTZCalibrateNode, SetPTZHomeNode, SetPTZPresetNode
from remander.workflows.nodes.save_restore import RestoreBitmasksNode, SaveBitmasksNode
from remander.workflows.state import WorkflowDeps, WorkflowState
from tests.factories import create_camera, create_command, create_power_device


def _make_ctx(state, deps):
    ctx = MagicMock(spec=GraphRunContext)
    ctx.state = state
    ctx.deps = deps
    return ctx


def _make_deps(**overrides):
    defaults = {
        "nvr_client": AsyncMock(),
        "tapo_client": AsyncMock(),
        "sonoff_client": AsyncMock(),
        "notification_sender": AsyncMock(),
        "latitude": 40.7128,
        "longitude": -74.0060,
    }
    defaults.update(overrides)
    return WorkflowDeps(**defaults)


def _make_state(**overrides):
    defaults = {
        "command_id": 1,
        "command_type": CommandType.SET_AWAY_NOW,
        "device_ids": [],
    }
    defaults.update(overrides)
    return WorkflowState(**defaults)


class TestSaveBitmasksNode:
    async def test_saves_current_bitmasks(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Save Cam", channel=0)

        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )

        deps = _make_deps()
        deps.nvr_client.get_alarm_schedule.return_value = "000000111111111111110000"
        deps.nvr_client.get_detection_zones.return_value = "1" * 4800

        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SaveBitmasksNode()
        with patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        saved = await SavedDeviceState.filter(command_id=cmd.id, device_id=camera.id)
        assert len(saved) == 1
        assert saved[0].saved_hour_bitmask == "000000111111111111110000"
        assert saved[0].saved_zone_mask == "1" * 4800


class TestRestoreBitmasksNode:
    async def test_restores_saved_bitmasks(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Restore Cam", channel=0)

        await SavedDeviceState.create(
            command_id=cmd.id,
            device_id=camera.id,
            detection_type=DetectionType.MOTION,
            saved_hour_bitmask="000000111111111111110000",
            saved_zone_mask="1" * 4800,
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = RestoreBitmasksNode()
        with patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.set_alarm_schedule.assert_called_once_with(
            0, DetectionType.MOTION, "000000111111111111110000"
        )
        deps.nvr_client.set_detection_zones.assert_called_once_with(
            0, DetectionType.MOTION, "1" * 4800
        )


class TestPowerOnNode:
    async def test_powers_on_associated_devices(self) -> None:
        cmd = await create_command()
        power = await create_power_device(name="Plug 1", ip_address="192.168.1.10")
        camera = await create_camera(name="Powered Cam", power_device_id=power.id)

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PowerOnNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.tapo_client.turn_on.assert_called_once_with("192.168.1.10")

    async def test_skips_cameras_without_power_devices(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="No Power Cam")

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PowerOnNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.tapo_client.turn_on.assert_not_called()
        deps.sonoff_client.turn_on.assert_not_called()


class TestWaitForPowerOnNode:
    async def test_polls_until_online(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Poll Cam", channel=0, power_device_id=None)
        # Simulate: first check offline, second check online
        power = await create_power_device(name="Poll Plug")
        camera.power_device_id = power.id
        await camera.save()

        deps = _make_deps()
        deps.nvr_client.is_channel_online.side_effect = [False, True]
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = WaitForPowerOnNode()
        with (
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.asyncio.sleep", new_callable=AsyncMock),
        ):
            await node.run(ctx)

        assert deps.nvr_client.is_channel_online.call_count == 2

    async def test_timeout_logs_error(self) -> None:
        cmd = await create_command()
        power = await create_power_device(name="Timeout Plug")
        camera = await create_camera(name="Timeout Cam", channel=1, power_device_id=power.id)

        deps = _make_deps()
        # Always offline
        deps.nvr_client.is_channel_online.return_value = False
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = WaitForPowerOnNode(timeout_seconds=2, poll_interval_seconds=1)
        with (
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.asyncio.sleep", new_callable=AsyncMock),
        ):
            await node.run(ctx)

        assert state.has_errors is True
        assert state.device_results.get(camera.id) == "failed"


class TestPowerOffNode:
    async def test_powers_off_devices(self) -> None:
        cmd = await create_command()
        power = await create_power_device(name="Off Plug", ip_address="192.168.1.20")
        camera = await create_camera(name="Off Cam", power_device_id=power.id)

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PowerOffNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.tapo_client.turn_off.assert_called_once_with("192.168.1.20")


class TestPTZNodes:
    async def test_set_ptz_preset_away(self) -> None:
        cmd = await create_command()
        camera = await create_camera(
            name="PTZ Cam",
            channel=0,
            has_ptz=True,
            ptz_away_preset=2,
            ptz_speed=30,
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SetPTZPresetNode()
        with patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.move_to_preset.assert_called_once_with(0, 2, 30)

    async def test_set_ptz_home(self) -> None:
        cmd = await create_command()
        camera = await create_camera(
            name="PTZ Home Cam",
            channel=1,
            has_ptz=True,
            ptz_home_preset=1,
            ptz_speed=20,
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SetPTZHomeNode()
        with patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.move_to_preset.assert_called_once_with(1, 1, 20)

    async def test_calibrate_ptz(self) -> None:
        cmd = await create_command()
        camera = await create_camera(
            name="Calib Cam",
            channel=0,
            has_ptz=True,
            ptz_away_preset=2,
            ptz_speed=30,
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PTZCalibrateNode()
        with patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        # Calibration calls move_to_preset (moves to preset and back)
        assert deps.nvr_client.move_to_preset.call_count >= 1


class TestSetNotificationBitmasksNode:
    async def test_applies_bitmasks(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Bitmask Cam", channel=0)

        from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask
        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )
        hb = await HourBitmask.create(name="Test HB", subtype="static", static_value="1" * 24)
        await DeviceBitmaskAssignment.create(
            device=camera,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            hour_bitmask=hb,
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SetNotificationBitmasksNode(mode=Mode.AWAY)
        with patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.set_alarm_schedule.assert_called_once()

    async def test_handles_per_device_failure(self) -> None:
        cmd = await create_command()
        cam1 = await create_camera(name="OK Cam", channel=0)
        cam2 = await create_camera(name="Fail Cam", channel=1)

        from remander.models.detection import DeviceDetectionType

        for cam in [cam1, cam2]:
            await DeviceDetectionType.create(
                device=cam, detection_type=DetectionType.MOTION, is_enabled=True
            )

        deps = _make_deps()
        # First call succeeds, second fails
        deps.nvr_client.set_alarm_schedule.side_effect = [None, Exception("NVR error")]

        state = _make_state(command_id=cmd.id, device_ids=[cam1.id, cam2.id])
        ctx = _make_ctx(state, deps)

        node = SetNotificationBitmasksNode(mode=Mode.AWAY)
        with patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        assert state.has_errors is True
        assert state.device_results.get(cam2.id) == "failed"


class TestSetZoneMasksNode:
    async def test_applies_zone_masks(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Zone Cam", channel=0)

        from remander.models.bitmask import DeviceBitmaskAssignment, ZoneMask
        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )
        zm = await ZoneMask.create(name="Full Frame", mask_value="1" * 4800)
        await DeviceBitmaskAssignment.create(
            device=camera,
            mode=Mode.AWAY,
            detection_type=DetectionType.MOTION,
            zone_mask=zm,
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SetZoneMasksNode(mode=Mode.AWAY)
        with patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.set_detection_zones.assert_called_once()

    async def test_handles_per_device_failure(self) -> None:
        cmd = await create_command()
        cam1 = await create_camera(name="OK Zone Cam", channel=0)
        cam2 = await create_camera(name="Fail Zone Cam", channel=1)

        from remander.models.detection import DeviceDetectionType

        for cam in [cam1, cam2]:
            await DeviceDetectionType.create(
                device=cam, detection_type=DetectionType.MOTION, is_enabled=True
            )

        deps = _make_deps()
        deps.nvr_client.set_detection_zones.side_effect = [None, Exception("NVR error")]

        state = _make_state(command_id=cmd.id, device_ids=[cam1.id, cam2.id])
        ctx = _make_ctx(state, deps)

        node = SetZoneMasksNode(mode=Mode.AWAY)
        with patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        assert state.has_errors is True
