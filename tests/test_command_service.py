"""Tests for the command service — RED phase (TDD)."""

import pytest

from remander.models.command import Command
from remander.models.enums import CommandStatus, CommandType
from remander.services.command import (
    cancel_command,
    create_command,
    get_active_command,
    get_command,
    get_next_queued,
    list_commands,
    set_error_summary,
    transition_status,
)
from tests.factories import create_command as factory_command


class TestCreateCommand:
    async def test_create_set_away_now(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_NOW,
            initiated_by_ip="192.168.1.50",
        )
        assert cmd.id is not None
        assert cmd.command_type == CommandType.SET_AWAY_NOW
        assert cmd.status == CommandStatus.PENDING
        assert cmd.initiated_by_ip == "192.168.1.50"
        assert cmd.created_at is not None

    async def test_create_with_user(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_HOME_NOW,
            initiated_by_ip="10.0.0.1",
            initiated_by_user="alice",
        )
        assert cmd.initiated_by_user == "alice"

    async def test_create_with_tag_filter(self) -> None:
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            tag_filter="front-yard,indoor",
        )
        assert cmd.tag_filter == "front-yard,indoor"

    async def test_create_with_delay_minutes(self) -> None:
        cmd = await create_command(
            command_type=CommandType.SET_AWAY_DELAYED,
            delay_minutes=15,
        )
        assert cmd.delay_minutes == 15

    async def test_create_with_pause_minutes(self) -> None:
        cmd = await create_command(
            command_type=CommandType.PAUSE_NOTIFICATIONS,
            pause_minutes=30,
        )
        assert cmd.pause_minutes == 30


class TestGetCommand:
    async def test_get_existing(self) -> None:
        cmd = await factory_command()
        fetched = await get_command(cmd.id)
        assert fetched is not None
        assert fetched.id == cmd.id

    async def test_get_nonexistent(self) -> None:
        result = await get_command(99999)
        assert result is None


class TestListCommands:
    async def test_list_all(self) -> None:
        await factory_command(command_type=CommandType.SET_AWAY_NOW)
        await factory_command(command_type=CommandType.SET_HOME_NOW)
        result = await list_commands()
        assert len(result) == 2

    async def test_list_filter_by_status(self) -> None:
        await factory_command(status=CommandStatus.PENDING)
        await factory_command(status=CommandStatus.SUCCEEDED)
        result = await list_commands(status=CommandStatus.PENDING)
        assert len(result) == 1
        assert result[0].status == CommandStatus.PENDING

    async def test_list_with_limit(self) -> None:
        for _ in range(5):
            await factory_command()
        result = await list_commands(limit=3)
        assert len(result) == 3

    async def test_list_ordered_by_created_at_desc(self) -> None:
        """Most recent commands should come first."""
        cmd1 = await factory_command(command_type=CommandType.SET_AWAY_NOW)
        cmd2 = await factory_command(command_type=CommandType.SET_HOME_NOW)
        result = await list_commands()
        assert result[0].id == cmd2.id
        assert result[1].id == cmd1.id


class TestTransitionStatus:
    async def test_pending_to_queued(self) -> None:
        cmd = await factory_command(status=CommandStatus.PENDING)
        updated = await transition_status(cmd.id, CommandStatus.QUEUED)
        assert updated is not None
        assert updated.status == CommandStatus.QUEUED
        assert updated.queued_at is not None

    async def test_queued_to_running(self) -> None:
        cmd = await factory_command(status=CommandStatus.QUEUED)
        updated = await transition_status(cmd.id, CommandStatus.RUNNING)
        assert updated is not None
        assert updated.status == CommandStatus.RUNNING
        assert updated.started_at is not None

    async def test_running_to_succeeded(self) -> None:
        cmd = await factory_command(status=CommandStatus.RUNNING)
        updated = await transition_status(cmd.id, CommandStatus.SUCCEEDED)
        assert updated is not None
        assert updated.status == CommandStatus.SUCCEEDED
        assert updated.completed_at is not None

    async def test_running_to_failed(self) -> None:
        cmd = await factory_command(status=CommandStatus.RUNNING)
        updated = await transition_status(cmd.id, CommandStatus.FAILED)
        assert updated is not None
        assert updated.status == CommandStatus.FAILED
        assert updated.completed_at is not None

    async def test_running_to_completed_with_errors(self) -> None:
        cmd = await factory_command(status=CommandStatus.RUNNING)
        updated = await transition_status(cmd.id, CommandStatus.COMPLETED_WITH_ERRORS)
        assert updated is not None
        assert updated.status == CommandStatus.COMPLETED_WITH_ERRORS
        assert updated.completed_at is not None

    async def test_pending_to_cancelled(self) -> None:
        cmd = await factory_command(status=CommandStatus.PENDING)
        updated = await transition_status(cmd.id, CommandStatus.CANCELLED)
        assert updated is not None
        assert updated.status == CommandStatus.CANCELLED
        assert updated.completed_at is not None

    async def test_queued_to_cancelled(self) -> None:
        cmd = await factory_command(status=CommandStatus.QUEUED)
        updated = await transition_status(cmd.id, CommandStatus.CANCELLED)
        assert updated is not None
        assert updated.status == CommandStatus.CANCELLED

    async def test_running_to_cancelled(self) -> None:
        cmd = await factory_command(status=CommandStatus.RUNNING)
        updated = await transition_status(cmd.id, CommandStatus.CANCELLED)
        assert updated is not None
        assert updated.status == CommandStatus.CANCELLED

    async def test_invalid_transition_raises(self) -> None:
        """Cannot go from succeeded back to running."""
        cmd = await factory_command(status=CommandStatus.SUCCEEDED)
        with pytest.raises(ValueError, match="Invalid"):
            await transition_status(cmd.id, CommandStatus.RUNNING)

    async def test_transition_nonexistent_returns_none(self) -> None:
        result = await transition_status(99999, CommandStatus.QUEUED)
        assert result is None


class TestCancelCommand:
    async def test_cancel_pending(self) -> None:
        cmd = await factory_command(status=CommandStatus.PENDING)
        result = await cancel_command(cmd.id)
        assert result is True
        updated = await Command.get(id=cmd.id)
        assert updated.status == CommandStatus.CANCELLED

    async def test_cancel_queued(self) -> None:
        cmd = await factory_command(status=CommandStatus.QUEUED)
        result = await cancel_command(cmd.id)
        assert result is True

    async def test_cancel_completed_raises(self) -> None:
        cmd = await factory_command(status=CommandStatus.SUCCEEDED)
        with pytest.raises(ValueError, match="Cannot cancel"):
            await cancel_command(cmd.id)

    async def test_cancel_nonexistent_returns_false(self) -> None:
        result = await cancel_command(99999)
        assert result is False


class TestGetNextQueued:
    async def test_returns_oldest_queued(self) -> None:
        """FIFO: oldest queued command should be returned first."""
        cmd1 = await factory_command(status=CommandStatus.QUEUED)
        await factory_command(status=CommandStatus.QUEUED)
        result = await get_next_queued()
        assert result is not None
        assert result.id == cmd1.id

    async def test_returns_none_when_no_queued(self) -> None:
        await factory_command(status=CommandStatus.PENDING)
        result = await get_next_queued()
        assert result is None


class TestGetActiveCommand:
    async def test_returns_running_command(self) -> None:
        cmd = await factory_command(status=CommandStatus.RUNNING)
        result = await get_active_command()
        assert result is not None
        assert result.id == cmd.id

    async def test_returns_none_when_no_active(self) -> None:
        await factory_command(status=CommandStatus.PENDING)
        result = await get_active_command()
        assert result is None


class TestSetErrorSummary:
    async def test_set_error_summary(self) -> None:
        cmd = await factory_command(status=CommandStatus.FAILED)
        updated = await set_error_summary(cmd.id, "NVR login failed: timeout")
        assert updated is not None
        assert updated.error_summary == "NVR login failed: timeout"

    async def test_set_error_summary_nonexistent(self) -> None:
        result = await set_error_summary(99999, "error")
        assert result is None
