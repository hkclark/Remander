"""Tests for infrastructure workflow nodes — RED phase (TDD)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_graph import End, GraphRunContext

from remander.models.enums import ActivityStatus, CommandType, DetectionType
from remander.workflows.nodes.delay import OptionalDelayNode
from remander.workflows.nodes.filter import FilterByTagNode
from remander.workflows.nodes.notify import NotifyNode
from remander.workflows.nodes.nvr import NVRLoginNode, NVRLogoutNode
from remander.workflows.nodes.power import PowerOnNode
from remander.workflows.nodes.save_restore import RestoreBitmasksNode, SaveBitmasksNode
from remander.workflows.nodes.validate import ValidateNode
from remander.workflows.state import WorkflowDeps, WorkflowState
from tests.factories import create_camera, create_command


def _make_ctx(
    state: WorkflowState, deps: WorkflowDeps
) -> GraphRunContext[WorkflowState, WorkflowDeps]:
    """Create a GraphRunContext for testing."""
    ctx = MagicMock(spec=GraphRunContext)
    ctx.state = state
    ctx.deps = deps
    return ctx


def _make_deps(**overrides: object) -> WorkflowDeps:
    """Create WorkflowDeps with mocked clients."""
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


def _make_state(**overrides: object) -> WorkflowState:
    """Create a WorkflowState with defaults."""
    defaults = {
        "command_id": 1,
        "command_type": CommandType.SET_AWAY_NOW,
        "device_ids": [],
    }
    defaults.update(overrides)
    return WorkflowState(**defaults)


class TestNVRLoginNode:
    async def test_calls_login(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        state = _make_state(command_id=cmd.id)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        await node.run(ctx)
        deps.nvr_client.login.assert_called_once()

    async def test_logs_activity_on_success(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        state = _make_state(command_id=cmd.id)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        with patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock) as mock_log:
            await node.run(ctx)
            mock_log.assert_called()
            # Check that it logged as SUCCEEDED
            calls = mock_log.call_args_list
            statuses = [c.kwargs.get("status") or c.args[2] for c in calls]
            assert any(s == ActivityStatus.SUCCEEDED for s in statuses)

    async def test_handles_login_failure(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        deps.nvr_client.login.side_effect = Exception("Connection refused")
        state = _make_state(command_id=cmd.id)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        with patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Connection refused"):
                await node.run(ctx)


class TestNVRLoginNodeRouting:
    """NVRLoginNode must route SET_AWAY to PowerOn, pause to SaveBitmasks, home to RestoreBitmasks."""

    async def test_set_away_routes_to_power_on(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, command_type=CommandType.SET_AWAY_NOW)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        with patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, PowerOnNode)

    async def test_set_away_delayed_routes_to_power_on(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_DELAYED)
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, command_type=CommandType.SET_AWAY_DELAYED)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        with patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, PowerOnNode)

    async def test_pause_notifications_routes_to_save_bitmasks(self) -> None:
        cmd = await create_command(command_type=CommandType.PAUSE_NOTIFICATIONS)
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, command_type=CommandType.PAUSE_NOTIFICATIONS)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        with patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, SaveBitmasksNode)

    async def test_set_home_routes_to_restore_bitmasks(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, command_type=CommandType.SET_HOME_NOW)
        ctx = _make_ctx(state, deps)

        node = NVRLoginNode()
        with patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, RestoreBitmasksNode)


class TestNVRLogoutNode:
    async def test_calls_logout(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        state = _make_state(command_id=cmd.id)
        ctx = _make_ctx(state, deps)

        node = NVRLogoutNode()
        await node.run(ctx)
        deps.nvr_client.logout.assert_called_once()


class TestOptionalDelayNode:
    async def test_skips_when_no_delay(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, delay_minutes=None)
        ctx = _make_ctx(state, deps)

        node = OptionalDelayNode()
        # Should return quickly without sleeping
        result = await node.run(ctx)
        assert result is not None  # Returns next node

    async def test_sleeps_when_delay_set(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, delay_minutes=1)
        ctx = _make_ctx(state, deps)

        node = OptionalDelayNode()
        sleep_target = "remander.workflows.nodes.delay.asyncio.sleep"
        with patch(sleep_target, new_callable=AsyncMock) as mock_sleep:
            await node.run(ctx)
            mock_sleep.assert_called_once_with(60)  # 1 minute = 60 seconds

    async def test_skips_when_delay_is_zero(self) -> None:
        cmd = await create_command()
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, delay_minutes=0)
        ctx = _make_ctx(state, deps)

        node = OptionalDelayNode()
        sleep_target = "remander.workflows.nodes.delay.asyncio.sleep"
        with patch(sleep_target, new_callable=AsyncMock) as mock_sleep:
            await node.run(ctx)
            mock_sleep.assert_not_called()


class TestFilterByTagNode:
    async def test_filters_to_tagged_devices(self) -> None:
        cmd = await create_command()
        cam1 = await create_camera(name="Tagged Cam")
        cam2 = await create_camera(name="Untagged Cam")

        from remander.models.tag import Tag

        tag = await Tag.create(name="outdoor")
        await cam1.tags.add(tag)

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[cam1.id, cam2.id], tag_filter="outdoor")
        ctx = _make_ctx(state, deps)

        node = FilterByTagNode()
        await node.run(ctx)
        assert ctx.state.device_ids == [cam1.id]

    async def test_passes_through_when_no_filter(self) -> None:
        cmd = await create_command()
        cam1 = await create_camera(name="Pass Cam 1")
        cam2 = await create_camera(name="Pass Cam 2")

        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[cam1.id, cam2.id], tag_filter=None)
        ctx = _make_ctx(state, deps)

        node = FilterByTagNode()
        await node.run(ctx)
        assert len(ctx.state.device_ids) == 2


class TestNotifyNode:
    async def test_calls_notification_sender(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(command_id=cmd.id)
        ctx = _make_ctx(state, deps)

        node = NotifyNode()
        await node.run(ctx)
        deps.notification_sender.send.assert_called_once()

    async def test_handles_send_failure_gracefully(self) -> None:
        """Notification failure should not crash the workflow."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        deps.notification_sender.send.side_effect = Exception("SMTP timeout")
        state = _make_state(command_id=cmd.id)
        ctx = _make_ctx(state, deps)

        node = NotifyNode()
        with patch("remander.workflows.nodes.notify.log_activity", new_callable=AsyncMock):
            # Should NOT raise — notification failure is non-fatal
            result = await node.run(ctx)
            assert isinstance(result, End)


class TestValidateNode:
    async def test_passes_when_bitmasks_match(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Valid Cam", channel=0)
        deps = _make_deps()
        deps.nvr_client.get_alarm_schedule.return_value = "1" * 24
        deps.nvr_client.get_detection_zones.return_value = "1" * 4800

        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        state.expected_bitmasks[camera.id] = {
            DetectionType.MOTION: {
                "hour_bitmask": "1" * 24,
                "zone_mask": "1" * 4800,
            }
        }
        ctx = _make_ctx(state, deps)

        node = ValidateNode()
        with patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock):
            await node.run(ctx)
        assert len(state.validation_discrepancies) == 0

    async def test_detects_hour_bitmask_mismatch(self) -> None:
        cmd = await create_command()
        camera = await create_camera(name="Mismatch Cam", channel=1)
        deps = _make_deps()
        deps.nvr_client.get_alarm_schedule.return_value = "0" * 24  # actual
        deps.nvr_client.get_detection_zones.return_value = "1" * 4800

        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        state.expected_bitmasks[camera.id] = {
            DetectionType.MOTION: {
                "hour_bitmask": "1" * 24,  # expected
                "zone_mask": "1" * 4800,
            }
        }
        ctx = _make_ctx(state, deps)

        node = ValidateNode()
        with patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock):
            await node.run(ctx)
        assert len(state.validation_discrepancies) > 0

    async def test_skips_devices_without_expectations(self) -> None:
        """Devices not in expected_bitmasks should be skipped."""
        cmd = await create_command()
        camera = await create_camera(name="Skip Cam", channel=2)
        deps = _make_deps()
        state = _make_state(command_id=cmd.id, device_ids=[camera.id])
        # No expected_bitmasks for this camera
        ctx = _make_ctx(state, deps)

        node = ValidateNode()
        with patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock):
            await node.run(ctx)
        assert len(state.validation_discrepancies) == 0
