"""Tests for IngressEgressMuteNode and WaitForMuteExpiryNode — RED phase (TDD)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_graph import GraphRunContext

from remander.models.enums import CommandType, DetectionType
from remander.workflows.nodes.delay import OptionalDelayNode
from remander.workflows.nodes.mute import IngressEgressMuteNode, WaitForMuteExpiryNode
from remander.workflows.nodes.nvr import NVRLoginNode
from remander.workflows.state import WorkflowDeps, WorkflowState
from tests.factories import create_camera, create_command


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
        "latitude": 0.0,
        "longitude": 0.0,
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


class TestIngressEgressMuteNodeSkip:
    async def test_away_skips_to_optional_delay_when_no_mute_devices(self) -> None:
        """When mute_tag_device_ids is empty, AWAY routes to OptionalDelayNode."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_tag_device_ids=[],
        )
        ctx = _make_ctx(state, deps)

        node = IngressEgressMuteNode()
        result = await node.run(ctx)

        assert isinstance(result, OptionalDelayNode)
        deps.nvr_client.login.assert_not_called()
        assert state.mute_start_time is None

    async def test_home_skips_to_nvr_login_when_no_mute_devices(self) -> None:
        """When mute_tag_device_ids is empty, HOME routes to NVRLoginNode."""
        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_HOME_NOW,
            mute_tag_device_ids=[],
        )
        ctx = _make_ctx(state, deps)

        node = IngressEgressMuteNode()
        result = await node.run(ctx)

        assert isinstance(result, NVRLoginNode)
        deps.nvr_client.login.assert_not_called()


class TestIngressEgressMuteNodeMutes:
    async def test_sets_24_zeros_on_mute_devices(self) -> None:
        """When mute devices are configured, sets alarm schedule to 24 zeros."""
        from remander.models.detection import DeviceDetectionType

        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        cam = await create_camera(name="Mute Cam", channel=3)
        await DeviceDetectionType.create(
            device=cam, detection_type=DetectionType.MOTION, is_enabled=True
        )

        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_tag_device_ids=[cam.id],
            mute_duration_seconds=180,
        )
        ctx = _make_ctx(state, deps)

        node = IngressEgressMuteNode()
        with patch("remander.workflows.nodes.mute.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        deps.nvr_client.login.assert_called_once()
        deps.nvr_client.set_alarm_schedule.assert_called_once_with(
            3, DetectionType.MOTION, "0" * 24
        )
        deps.nvr_client.logout.assert_called_once()

    async def test_records_mute_start_time(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        cam = await create_camera(name="Time Cam", channel=0)

        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_tag_device_ids=[cam.id],
            mute_duration_seconds=120,
        )
        ctx = _make_ctx(state, deps)

        before = datetime.now(UTC)
        node = IngressEgressMuteNode()
        with patch("remander.workflows.nodes.mute.log_activity", new_callable=AsyncMock):
            await node.run(ctx)
        after = datetime.now(UTC)

        assert state.mute_start_time is not None
        assert before <= state.mute_start_time <= after

    async def test_away_routes_to_optional_delay_after_muting(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        cam = await create_camera(name="Away Mute Cam", channel=0)

        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_tag_device_ids=[cam.id],
            mute_duration_seconds=60,
        )
        ctx = _make_ctx(state, deps)

        node = IngressEgressMuteNode()
        with patch("remander.workflows.nodes.mute.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, OptionalDelayNode)

    async def test_home_routes_to_nvr_login_after_muting(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        cam = await create_camera(name="Home Mute Cam", channel=0)

        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_HOME_NOW,
            mute_tag_device_ids=[cam.id],
            mute_duration_seconds=60,
        )
        ctx = _make_ctx(state, deps)

        node = IngressEgressMuteNode()
        with patch("remander.workflows.nodes.mute.log_activity", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, NVRLoginNode)

    async def test_skips_device_without_channel(self) -> None:
        """Devices without a channel (no NVR channel) are skipped silently."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        cam = await create_camera(name="No Channel Cam")  # channel=None by default

        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_tag_device_ids=[cam.id],
            mute_duration_seconds=60,
        )
        ctx = _make_ctx(state, deps)

        node = IngressEgressMuteNode()
        with patch("remander.workflows.nodes.mute.log_activity", new_callable=AsyncMock):
            await node.run(ctx)

        deps.nvr_client.set_alarm_schedule.assert_not_called()


class TestWaitForMuteExpiryNode:
    async def test_skips_when_no_start_time(self) -> None:
        """If mute_start_time is None (mute was skipped), WaitForMuteExpiry skips immediately."""
        from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode

        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_start_time=None,
            mute_duration_seconds=180,
        )
        ctx = _make_ctx(state, deps)

        node = WaitForMuteExpiryNode()
        with patch("remander.workflows.nodes.mute.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await node.run(ctx)

        mock_sleep.assert_not_called()

    async def test_skips_when_mute_already_expired(self) -> None:
        """If mute_duration has already passed, does not sleep."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_start_time=datetime.now(UTC) - timedelta(seconds=300),  # 5 min ago
            mute_duration_seconds=60,  # 1 min duration — already expired
        )
        ctx = _make_ctx(state, deps)

        node = WaitForMuteExpiryNode()
        with patch("remander.workflows.nodes.mute.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await node.run(ctx)

        mock_sleep.assert_not_called()

    async def test_sleeps_for_remaining_duration(self) -> None:
        """Sleeps for the remaining time if mute hasn't expired yet."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_start_time=datetime.now(UTC) - timedelta(seconds=30),  # started 30s ago
            mute_duration_seconds=120,  # 2 min total — 90s remaining
        )
        ctx = _make_ctx(state, deps)

        node = WaitForMuteExpiryNode()
        with patch("remander.workflows.nodes.mute.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await node.run(ctx)

        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 85 <= sleep_duration <= 95  # ~90s, allow small timing slack

    async def test_away_routes_to_set_notification_bitmasks_away(self) -> None:
        from remander.models.enums import Mode
        from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode

        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            mute_start_time=None,
            mute_duration_seconds=60,
        )
        ctx = _make_ctx(state, deps)

        node = WaitForMuteExpiryNode()
        with patch("remander.workflows.nodes.mute.asyncio.sleep", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, SetNotificationBitmasksNode)
        assert result.mode == Mode.AWAY

    async def test_home_routes_to_set_notification_bitmasks_home(self) -> None:
        from remander.models.enums import Mode
        from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode

        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        deps = _make_deps()
        state = _make_state(
            command_id=cmd.id,
            command_type=CommandType.SET_HOME_NOW,
            mute_start_time=None,
            mute_duration_seconds=60,
        )
        ctx = _make_ctx(state, deps)

        node = WaitForMuteExpiryNode()
        with patch("remander.workflows.nodes.mute.asyncio.sleep", new_callable=AsyncMock):
            result = await node.run(ctx)

        assert isinstance(result, SetNotificationBitmasksNode)
        assert result.mode == Mode.HOME
