"""Tests for device operation workflow nodes — RED phase (TDD)."""

from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_graph import GraphRunContext

from remander.models.enums import (
    ActivityStatus,
    CommandType,
    DetectionType,
    Mode,
)
from remander.models.state import SavedDeviceState
from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode, SetZoneMasksNode
from remander.workflows.nodes.power import PowerOffNode, PowerOnNode, WaitForPowerOnNode
from remander.workflows.nodes.ptz import PTZCalibrateNode, SetPTZHomeNode, SetPTZPresetNode
from remander.workflows.nodes.save_restore import SaveBitmasksNode, RestoreBitmasksNode
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
        camera = await create_camera(name="Save Cam", channel=0, zone_masks_enabled=True)

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

    async def test_passes_timeout_from_deps_to_wait_node(self) -> None:
        """PowerOnNode must instantiate WaitForPowerOnNode with timeout values from WorkflowDeps."""
        cmd = await create_command()
        camera = await create_camera(name="Timeout Deps Cam")

        deps = _make_deps(power_on_timeout_seconds=75, power_on_poll_interval_seconds=5)
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PowerOnNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, WaitForPowerOnNode)
        assert result.timeout_seconds == 75
        assert result.poll_interval_seconds == 5

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


class TestWaitForPowerOnNodeRouting:
    """WaitForPowerOnNode routes to PTZCalibrateNode for AWAY, SaveBitmasksNode for PAUSE."""

    async def test_away_routes_to_ptz_calibrate_when_no_power_cameras(self) -> None:
        """AWAY cameras without power devices skip the wait — next node is PTZCalibrateNode."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        camera = await create_camera(name="No Power Routing Cam")  # no power_device_id

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = WaitForPowerOnNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, PTZCalibrateNode)

    async def test_away_routes_to_ptz_calibrate_after_power_on(self) -> None:
        """AWAY: once a camera comes online, next node is PTZCalibrateNode (no save needed)."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        power = await create_power_device(name="Routing Plug")
        camera = await create_camera(name="Power Routing Cam", channel=0, power_device_id=power.id)

        deps = _make_deps()
        deps.nvr_client.is_channel_online.return_value = True  # immediately online
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = WaitForPowerOnNode()
        with (
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await node.run(ctx)

        assert isinstance(result, PTZCalibrateNode)

    async def test_pause_routes_to_save_bitmasks_when_no_power_cameras(self) -> None:
        """PAUSE cameras without power devices skip the wait — next node is SaveBitmasks."""
        cmd = await create_command(command_type=CommandType.PAUSE_NOTIFICATIONS)
        camera = await create_camera(name="No Power Pause Cam")  # no power_device_id

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, command_type=CommandType.PAUSE_NOTIFICATIONS, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = WaitForPowerOnNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, SaveBitmasksNode)


class TestSaveBitmasksNodeRouting:
    """SaveBitmasksNode must route SET_AWAY to PTZCalibrateNode, pause to SetNotificationBitmasks."""

    async def test_set_away_routes_to_ptz_calibrate(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        camera = await create_camera(name="Route Save Cam", channel=0)

        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
        )

        deps = _make_deps()
        deps.nvr_client.get_alarm_schedule.return_value = "0" * 24
        state = _make_state(
            command_id=cmd.id, command_type=CommandType.SET_AWAY_NOW, device_ids=[camera.id]
        )
        ctx = _make_ctx(state, deps)

        node = SaveBitmasksNode()
        with patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, PTZCalibrateNode)

    async def test_pause_routes_to_set_notification_bitmasks(self) -> None:
        cmd = await create_command(command_type=CommandType.PAUSE_NOTIFICATIONS)
        camera = await create_camera(name="Route Pause Cam", channel=0)

        deps = _make_deps()
        deps.nvr_client.get_alarm_schedule.return_value = "0" * 24
        state = _make_state(
            command_id=cmd.id, command_type=CommandType.PAUSE_NOTIFICATIONS, device_ids=[camera.id]
        )
        ctx = _make_ctx(state, deps)

        node = SaveBitmasksNode()
        with patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, SetNotificationBitmasksNode)


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
        assert state.device_results.get(camera.id) == "Timeout after 2s"


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
    async def test_calibrate_skips_devices_with_prior_errors(self) -> None:
        """PTZCalibrateNode must not attempt PTZ on cameras that failed power-on."""
        cmd = await create_command()
        camera = await create_camera(
            name="Failed Power Cam", channel=2, has_ptz=True, ptz_away_preset=1, ptz_speed=30
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        # Simulate power-on timeout recorded by WaitForPowerOnNode
        state.device_results[camera.id] = "Timeout after 120s"
        ctx = _make_ctx(state, deps)

        node = PTZCalibrateNode()
        with patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.move_to_preset.assert_not_called()

    async def test_set_ptz_preset_skips_devices_with_prior_errors(self) -> None:
        """SetPTZPresetNode must not attempt PTZ on cameras that failed power-on."""
        cmd = await create_command()
        camera = await create_camera(
            name="Failed Power Preset Cam", channel=3, has_ptz=True, ptz_away_preset=2, ptz_speed=30
        )

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        state.device_results[camera.id] = "Timeout after 120s"
        ctx = _make_ctx(state, deps)

        node = SetPTZPresetNode()
        with patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.move_to_preset.assert_not_called()

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

    async def test_set_ptz_home_waits_for_settle_before_power_off(self) -> None:
        """SetPTZHomeNode must sleep ptz_settle_seconds after the move so the camera
        physically reaches the home position before being powered off."""
        cmd = await create_command()
        camera = await create_camera(
            name="PTZ Settle Cam", channel=2, has_ptz=True, ptz_home_preset=1, ptz_speed=30
        )

        deps = _make_deps(ptz_settle_seconds=7)
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SetPTZHomeNode()
        with (
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.ptz.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            await node.run(ctx)

        mock_sleep.assert_awaited_once_with(7)

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

    async def test_calibrate_retries_on_transient_failure(self) -> None:
        """PTZCalibrateNode retries move_to_preset on failure with a back-off sleep."""
        cmd = await create_command()
        camera = await create_camera(
            name="Retry Calib Cam", channel=4, has_ptz=True, ptz_away_preset=0, ptz_speed=None
        )

        deps = _make_deps()
        # Fail first attempt, succeed on second
        deps.nvr_client.move_to_preset.side_effect = [Exception("no camera connected"), None]
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PTZCalibrateNode()
        with (
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock) as mock_log,
            patch("remander.workflows.nodes.ptz.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            await node.run(ctx)

        # Two attempts total — one sleep between them
        assert deps.nvr_client.move_to_preset.call_count == 2
        mock_sleep.assert_awaited_once()
        # Activity logged as SUCCEEDED (eventually succeeded)
        statuses = [c.kwargs.get("status") for c in mock_log.call_args_list]
        assert ActivityStatus.SUCCEEDED in statuses

    async def test_calibrate_logs_failed_after_all_retries_exhausted(self) -> None:
        """PTZCalibrateNode logs FAILED after exhausting all retry attempts."""
        cmd = await create_command()
        camera = await create_camera(
            name="All Fail Calib Cam", channel=5, has_ptz=True, ptz_away_preset=0, ptz_speed=None
        )

        deps = _make_deps()
        deps.nvr_client.move_to_preset.side_effect = Exception("no camera connected")
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = PTZCalibrateNode()
        with (
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock) as mock_log,
            patch("remander.workflows.nodes.ptz.asyncio.sleep", new_callable=AsyncMock),
        ):
            await node.run(ctx)

        statuses = [c.kwargs.get("status") for c in mock_log.call_args_list]
        assert ActivityStatus.FAILED in statuses
        assert ActivityStatus.SUCCEEDED not in statuses

    async def test_set_ptz_preset_retries_on_transient_failure(self) -> None:
        """SetPTZPresetNode retries move_to_preset on failure with a back-off sleep."""
        cmd = await create_command()
        camera = await create_camera(
            name="Retry Preset Cam", channel=6, has_ptz=True, ptz_away_preset=1, ptz_speed=None
        )

        deps = _make_deps()
        deps.nvr_client.move_to_preset.side_effect = [Exception("no camera connected"), None]
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        ctx = _make_ctx(state, deps)

        node = SetPTZPresetNode()
        with (
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock) as mock_log,
            patch("remander.workflows.nodes.ptz.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            await node.run(ctx)

        assert deps.nvr_client.move_to_preset.call_count == 2
        mock_sleep.assert_awaited_once()
        statuses = [c.kwargs.get("status") for c in mock_log.call_args_list]
        assert ActivityStatus.SUCCEEDED in statuses


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
        assert state.device_results.get(cam2.id) == "NVR error"


class TestSetZoneMasksNode:
    async def test_applies_zone_masks(self) -> None:
        cmd = await create_command()
        # zone_masks_enabled=True and zone_mask_away set so zone mask resolution returns a value
        camera = await create_camera(
            name="Zone Cam", channel=0, zone_masks_enabled=True, zone_mask_away="1" * 4800
        )

        from remander.models.detection import DeviceDetectionType

        await DeviceDetectionType.create(
            device=camera, detection_type=DetectionType.MOTION, is_enabled=True
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
        cam1 = await create_camera(
            name="OK Zone Cam", channel=0, zone_masks_enabled=True, zone_mask_away="1" * 4800
        )
        cam2 = await create_camera(
            name="Fail Zone Cam", channel=1, zone_masks_enabled=True, zone_mask_away="1" * 4800
        )

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

    async def test_home_mute_routes_to_validate_not_ptz_home(self) -> None:
        """When mute is active, HOME SetZoneMasks routes to ValidateNode (PTZ already ran)."""
        from remander.workflows.nodes.validate import ValidateNode

        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_HOME_NOW,
            mute_duration_seconds=120,
        )
        ctx = _make_ctx(state, deps)

        node = SetZoneMasksNode(mode=Mode.HOME)
        with patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, ValidateNode)


class TestMuteRoutingInNodes:
    """Verify that mute_duration_seconds triggers alternate routing in existing nodes."""

    async def test_set_ptz_preset_routes_to_wait_for_mute_expiry_when_mute_active(self) -> None:
        """When mute is active, SetPTZPresetNode routes to WaitForMuteExpiryNode."""
        from remander.workflows.nodes.mute import WaitForMuteExpiryNode

        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_duration_seconds=180,
        )
        ctx = _make_ctx(state, deps)

        node = SetPTZPresetNode()
        with patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, WaitForMuteExpiryNode)

    async def test_power_off_routes_to_wait_for_mute_expiry_when_mute_active(self) -> None:
        """When mute is active, PowerOffNode routes to WaitForMuteExpiryNode."""
        from remander.workflows.nodes.mute import WaitForMuteExpiryNode

        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_HOME_NOW,
            mute_duration_seconds=120,
        )
        ctx = _make_ctx(state, deps)

        node = PowerOffNode()
        with patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, WaitForMuteExpiryNode)
