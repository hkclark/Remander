"""Tests for workflow graph definitions — RED phase (TDD)."""

from unittest.mock import AsyncMock, patch

from remander.models.enums import CommandType, DetectionType, Mode
from remander.workflows.graphs import get_workflow_for_command
from remander.workflows.state import WorkflowDeps, WorkflowState
from tests.factories import create_camera, create_command


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


class TestGetWorkflowForCommand:
    def test_set_away_now(self) -> None:
        graph, start_node = get_workflow_for_command(CommandType.SET_AWAY_NOW)
        assert graph is not None
        assert start_node is not None

    def test_set_away_delayed(self) -> None:
        graph, start_node = get_workflow_for_command(CommandType.SET_AWAY_DELAYED)
        assert graph is not None

    def test_set_home_now(self) -> None:
        graph, start_node = get_workflow_for_command(CommandType.SET_HOME_NOW)
        assert graph is not None

    def test_pause_notifications(self) -> None:
        graph, start_node = get_workflow_for_command(CommandType.PAUSE_NOTIFICATIONS)
        assert graph is not None

    def test_pause_recording(self) -> None:
        graph, start_node = get_workflow_for_command(CommandType.PAUSE_RECORDING)
        assert graph is not None


class TestSetAwayWorkflow:
    async def test_runs_end_to_end(self) -> None:
        """Set Away workflow should run all nodes in order with mocked clients."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        camera = await create_camera(name="Away Cam", channel=0)

        deps = _make_deps()
        state = WorkflowState(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            device_ids=[camera.id],
        )

        graph, start_node = get_workflow_for_command(CommandType.SET_AWAY_NOW)

        with (
            patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.delay.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.notify.log_activity", new_callable=AsyncMock),
        ):
            result = await graph.run(start_node, state=state, deps=deps)
            assert result.output == "done"

        # Verify key operations were called
        deps.nvr_client.login.assert_called_once()
        deps.nvr_client.logout.assert_called_once()
        deps.notification_sender.send.assert_called_once()

    async def test_partial_failure(self) -> None:
        """Partial failure should set has_errors but still complete."""
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        cam1 = await create_camera(name="OK Away Cam", channel=0)
        cam2 = await create_camera(name="Fail Away Cam", channel=1)

        from remander.models.bitmask import DeviceBitmaskAssignment, HourBitmask
        from remander.models.detection import DeviceDetectionType

        hb = await HourBitmask.create(name="Test HB", subtype="static", static_value="1" * 24)
        for cam in [cam1, cam2]:
            await DeviceDetectionType.create(
                device=cam, detection_type=DetectionType.MOTION, is_enabled=True
            )
            await DeviceBitmaskAssignment.create(
                device=cam,
                mode=Mode.AWAY,
                detection_type=DetectionType.MOTION,
                hour_bitmask=hb,
            )

        deps = _make_deps()
        # First call succeeds, second fails
        deps.nvr_client.set_alarm_schedule.side_effect = [None, Exception("NVR error")]

        state = WorkflowState(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            device_ids=[cam1.id, cam2.id],
        )

        graph, start_node = get_workflow_for_command(CommandType.SET_AWAY_NOW)

        with (
            patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.delay.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.notify.log_activity", new_callable=AsyncMock),
        ):
            result = await graph.run(start_node, state=state, deps=deps)
            assert result.output == "done"
            assert result.state.has_errors is True


class TestSetHomeWorkflow:
    async def test_runs_end_to_end(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_HOME_NOW)
        camera = await create_camera(name="Home Cam", channel=0)

        deps = _make_deps()
        state = WorkflowState(
            command_id=cmd.id,
            command_type=CommandType.SET_HOME_NOW,
            device_ids=[camera.id],
        )

        graph, start_node = get_workflow_for_command(CommandType.SET_HOME_NOW)

        with (
            patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.notify.log_activity", new_callable=AsyncMock),
        ):
            result = await graph.run(start_node, state=state, deps=deps)
            assert result.output == "done"


class TestPauseNotificationsWorkflow:
    async def test_runs_end_to_end(self) -> None:
        cmd = await create_command(command_type=CommandType.PAUSE_NOTIFICATIONS)
        camera = await create_camera(name="Pause Cam", channel=0)

        deps = _make_deps()
        state = WorkflowState(
            command_id=cmd.id,
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            device_ids=[camera.id],
            pause_minutes=30,
        )

        graph, start_node = get_workflow_for_command(CommandType.PAUSE_NOTIFICATIONS)

        with (
            patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.filter.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.bitmask.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.notify.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.schedule.log_activity", new_callable=AsyncMock),
        ):
            result = await graph.run(start_node, state=state, deps=deps)
            assert result.output == "done"


class TestReArmWorkflow:
    async def test_runs_end_to_end(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        camera = await create_camera(name="ReArm Cam", channel=0)

        deps = _make_deps()
        state = WorkflowState(
            command_id=cmd.id,
            command_type=CommandType.SET_AWAY_NOW,
            device_ids=[camera.id],
            is_rearm=True,
        )

        graph, start_node = get_workflow_for_command("rearm")

        with (
            patch("remander.workflows.nodes.nvr.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.save_restore.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.ptz.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.power.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.validate.log_activity", new_callable=AsyncMock),
            patch("remander.workflows.nodes.notify.log_activity", new_callable=AsyncMock),
        ):
            result = await graph.run(start_node, state=state, deps=deps)
            assert result.output == "done"
