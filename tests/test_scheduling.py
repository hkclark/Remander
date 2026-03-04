"""Tests for delayed commands and re-arm scheduling — RED phase (TDD)."""

from unittest.mock import AsyncMock, patch

from remander.models.command import Command
from remander.models.enums import CommandStatus, CommandType
from remander.services.scheduling import (
    cancel_delayed_command,
    cancel_pending_rearms,
    schedule_delayed_command,
    schedule_rearm,
)
from tests.factories import create_command


class TestScheduleDelayedCommand:
    async def test_enqueues_saq_job_with_delay(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_DELAYED,
            delay_minutes=30,
            status=CommandStatus.QUEUED,
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.enqueue.return_value = AsyncMock(key="delayed-job-123")
            mock_get_queue.return_value = mock_queue
            await schedule_delayed_command(cmd.id, 30)

        mock_queue.enqueue.assert_called_once()
        call_kwargs = mock_queue.enqueue.call_args
        assert call_kwargs.kwargs.get("scheduled") is not None

    async def test_stores_job_id_on_command(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_DELAYED,
            delay_minutes=30,
            status=CommandStatus.QUEUED,
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.enqueue.return_value = AsyncMock(key="delayed-job-456")
            mock_get_queue.return_value = mock_queue
            await schedule_delayed_command(cmd.id, 30)

        updated = await Command.get(id=cmd.id)
        assert updated.saq_job_id == "delayed-job-456"


class TestCancelDelayedCommand:
    async def test_aborts_saq_job(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_DELAYED,
            delay_minutes=30,
            status=CommandStatus.QUEUED,
            saq_job_id="delayed-job-789",
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_delayed_command(cmd.id)

        mock_queue.abort.assert_called_once()

    async def test_clears_job_id(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_DELAYED,
            delay_minutes=30,
            status=CommandStatus.QUEUED,
            saq_job_id="delayed-job-789",
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_delayed_command(cmd.id)

        updated = await Command.get(id=cmd.id)
        assert updated.saq_job_id is None

    async def test_noop_when_no_job_id(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_DELAYED,
            status=CommandStatus.QUEUED,
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_delayed_command(cmd.id)

        mock_queue.abort.assert_not_called()


class TestScheduleRearm:
    async def test_enqueues_rearm_job_with_delay(self) -> None:
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            pause_minutes=60,
            status=CommandStatus.SUCCEEDED,
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.enqueue.return_value = AsyncMock(key="rearm-job-123")
            mock_get_queue.return_value = mock_queue
            await schedule_rearm(cmd.id, 60)

        mock_queue.enqueue.assert_called_once()
        call_kwargs = mock_queue.enqueue.call_args
        assert call_kwargs.kwargs.get("scheduled") is not None

    async def test_stores_rearm_job_id(self) -> None:
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            pause_minutes=60,
            status=CommandStatus.SUCCEEDED,
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.enqueue.return_value = AsyncMock(key="rearm-job-456")
            mock_get_queue.return_value = mock_queue
            await schedule_rearm(cmd.id, 60)

        updated = await Command.get(id=cmd.id)
        assert updated.saq_job_id == "rearm-job-456"


class TestCancelPendingRearms:
    async def test_cancels_all_rearm_jobs(self) -> None:
        await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            pause_minutes=30,
            status=CommandStatus.SUCCEEDED,
            saq_job_id="rearm-1",
        )
        await create_command(
            command_type=CommandType.PAUSE_RECORDING,
            pause_minutes=60,
            status=CommandStatus.SUCCEEDED,
            saq_job_id="rearm-2",
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_pending_rearms()

        assert mock_queue.abort.call_count == 2

    async def test_clears_job_ids(self) -> None:
        cmd1 = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            pause_minutes=30,
            status=CommandStatus.SUCCEEDED,
            saq_job_id="rearm-1",
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_pending_rearms()

        updated = await Command.get(id=cmd1.id)
        assert updated.saq_job_id is None

    async def test_ignores_non_pause_commands(self) -> None:
        await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            status=CommandStatus.SUCCEEDED,
            saq_job_id="job-1",
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_pending_rearms()

        mock_queue.abort.assert_not_called()

    async def test_ignores_commands_without_job_id(self) -> None:
        await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            pause_minutes=30,
            status=CommandStatus.SUCCEEDED,
        )
        with patch("remander.services.scheduling.get_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_get_queue.return_value = mock_queue
            await cancel_pending_rearms()

        mock_queue.abort.assert_not_called()
