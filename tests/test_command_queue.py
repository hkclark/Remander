"""Tests for command queueing and execution — RED phase (TDD)."""

from unittest.mock import AsyncMock, MagicMock, patch

from remander.models.command import Command
from remander.models.enums import CommandStatus, CommandType
from remander.services.queue import enqueue_command, execute_command
from tests.factories import create_camera, create_command, create_tag


class TestEnqueueCommand:
    async def test_transitions_to_queued(self) -> None:
        cmd = await create_command(status=CommandStatus.PENDING)
        with patch("remander.services.queue.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await enqueue_command(cmd.id)

        updated = await Command.get(id=cmd.id)
        assert updated.status == CommandStatus.QUEUED

    async def test_enqueues_saq_job(self) -> None:
        cmd = await create_command(status=CommandStatus.PENDING)
        with patch("remander.services.queue.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.enqueue.return_value = AsyncMock(key="job-123")
            mock_get_queue.return_value = mock_queue
            await enqueue_command(cmd.id)

        mock_queue.enqueue.assert_called_once()


class TestExecuteCommand:
    async def test_transitions_to_running_then_succeeded(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.QUEUED,
        )

        with patch("remander.services.queue.run_workflow", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None  # No errors
            await execute_command(cmd.id)

        updated = await Command.get(id=cmd.id)
        assert updated.status == CommandStatus.SUCCEEDED

    async def test_transitions_to_failed_on_error(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.QUEUED,
        )

        with patch("remander.services.queue.run_workflow", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Critical failure")
            await execute_command(cmd.id)

        updated = await Command.get(id=cmd.id)
        assert updated.status == CommandStatus.FAILED
        assert updated.error_summary is not None

    async def test_transitions_to_completed_with_errors(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.QUEUED,
        )

        with patch("remander.services.queue.run_workflow", new_callable=AsyncMock) as mock_run:
            # run_workflow returns True to indicate partial errors
            mock_run.return_value = True
            await execute_command(cmd.id)

        updated = await Command.get(id=cmd.id)
        assert updated.status == CommandStatus.COMPLETED_WITH_ERRORS

    async def test_skips_cancelled_command(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.CANCELLED,
        )

        with patch("remander.services.queue.run_workflow", new_callable=AsyncMock) as mock_run:
            await execute_command(cmd.id)
            mock_run.assert_not_called()

    async def test_mute_state_loaded_into_workflow_state(self) -> None:
        """When button has mute enabled, run_workflow populates mute fields in WorkflowState."""
        from remander.models.dashboard_button import DashboardButton
        from remander.models.enums import ButtonOperationType
        from remander.services.dashboard_button import save_button_mute_tags

        btn = await DashboardButton.create(
            name="Mute Away",
            operation_type=ButtonOperationType.AWAY,
            mute_notifications_enabled=True,
            mute_duration_seconds=90,
        )
        cam = await create_camera(name="Mute Cam")
        tag = await create_tag(name="mute-group")
        await cam.tags.add(tag)
        await save_button_mute_tags(btn.id, [tag.id])

        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.QUEUED,
            dashboard_button_id=btn.id,
        )

        captured_states: list = []

        async def fake_graph_run(start_node, *, state, deps):
            captured_states.append(state)
            result = MagicMock()
            result.state = state
            result.state.has_errors = False
            return result

        mock_graph = MagicMock()
        mock_graph.run = fake_graph_run

        _settings = MagicMock(
            latitude=0.0, longitude=0.0, timezone="UTC",
            power_on_timeout_seconds=120, power_on_poll_interval_seconds=10,
            ptz_settle_seconds=10,
            nvr_host="localhost", nvr_port=8080, nvr_username="admin",
            nvr_password=MagicMock(get_secret_value=lambda: "pass"),
            nvr_use_https=False,
            smtp_host="", smtp_port=587, smtp_username="", smtp_use_tls=False,
            smtp_password=MagicMock(get_secret_value=lambda: ""),
            smtp_from="", smtp_to="",
        )
        with (
            patch("remander.config.get_settings", return_value=_settings),
            patch("remander.clients.reolink.ReolinkNVRClient"),
            patch("remander.clients.tapo.TapoClient"),
            patch("remander.clients.sonoff.SonoffClient"),
            patch("remander.clients.email.EmailNotificationSender"),
            patch("remander.workflows.graphs.get_workflow_for_command", return_value=(mock_graph, MagicMock())),
        ):
            from remander.services.queue import run_workflow
            await run_workflow(cmd)

        assert len(captured_states) == 1
        state = captured_states[0]
        assert state.mute_duration_seconds == 90
        assert cam.id in state.mute_tag_device_ids

    async def test_mute_graph_selected_when_mute_enabled(self) -> None:
        """When button has mute enabled, get_workflow_for_command is called with mute_enabled=True."""
        from remander.models.dashboard_button import DashboardButton
        from remander.models.enums import ButtonOperationType

        btn = await DashboardButton.create(
            name="Mute Home",
            operation_type=ButtonOperationType.HOME,
            mute_notifications_enabled=True,
            mute_duration_seconds=60,
        )
        cmd = await create_command(
            command_type=CommandType.SET_HOME_NOW,
            status=CommandStatus.QUEUED,
            dashboard_button_id=btn.id,
        )

        mock_graph = MagicMock()

        async def fake_graph_run(start_node, *, state, deps):
            result = MagicMock()
            result.state = state
            result.state.has_errors = False
            return result

        mock_graph.run = fake_graph_run

        _settings = MagicMock(
            latitude=0.0, longitude=0.0, timezone="UTC",
            power_on_timeout_seconds=120, power_on_poll_interval_seconds=10,
            ptz_settle_seconds=10,
            nvr_host="localhost", nvr_port=8080, nvr_username="admin",
            nvr_password=MagicMock(get_secret_value=lambda: "pass"),
            nvr_use_https=False,
            smtp_host="", smtp_port=587, smtp_username="", smtp_use_tls=False,
            smtp_password=MagicMock(get_secret_value=lambda: ""),
            smtp_from="", smtp_to="",
        )
        with (
            patch("remander.config.get_settings", return_value=_settings),
            patch("remander.clients.reolink.ReolinkNVRClient"),
            patch("remander.clients.tapo.TapoClient"),
            patch("remander.clients.sonoff.SonoffClient"),
            patch("remander.clients.email.EmailNotificationSender"),
            patch("remander.workflows.graphs.get_workflow_for_command", return_value=(mock_graph, MagicMock())) as mock_gwfc,
        ):
            from remander.services.queue import run_workflow
            await run_workflow(cmd)

        mock_gwfc.assert_called_once_with(CommandType.SET_HOME_NOW, mute_enabled=True)

    async def test_fifo_ordering(self) -> None:
        """Commands should execute in creation order."""
        cmd1 = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.QUEUED,
        )
        await create_command(
            command_type=CommandType.SET_HOME_NOW,
            status=CommandStatus.QUEUED,
        )

        from remander.services.command import get_next_queued

        next_cmd = await get_next_queued()
        assert next_cmd is not None
        assert next_cmd.id == cmd1.id
