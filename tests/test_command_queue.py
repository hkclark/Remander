"""Tests for command queueing and execution — RED phase (TDD)."""

from unittest.mock import AsyncMock, patch

from remander.models.command import Command
from remander.models.enums import CommandStatus, CommandType
from remander.services.queue import enqueue_command, execute_command
from tests.factories import create_command


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
