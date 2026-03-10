"""Command service — create, manage, and transition commands through their lifecycle."""

from datetime import datetime, timezone

from remander.models.command import Command
from remander.models.enums import CommandStatus, CommandType

# Valid state transitions: current_status -> set of allowed next statuses
VALID_TRANSITIONS: dict[CommandStatus, set[CommandStatus]] = {
    CommandStatus.PENDING: {CommandStatus.QUEUED, CommandStatus.CANCELLED},
    CommandStatus.QUEUED: {CommandStatus.RUNNING, CommandStatus.CANCELLED},
    CommandStatus.RUNNING: {
        CommandStatus.SUCCEEDED,
        CommandStatus.FAILED,
        CommandStatus.CANCELLED,
        CommandStatus.COMPLETED_WITH_ERRORS,
    },
    CommandStatus.SUCCEEDED: set(),
    CommandStatus.FAILED: set(),
    CommandStatus.CANCELLED: set(),
    CommandStatus.COMPLETED_WITH_ERRORS: set(),
}

# Statuses that can be cancelled
CANCELLABLE_STATUSES = {CommandStatus.PENDING, CommandStatus.QUEUED, CommandStatus.RUNNING}

# Terminal statuses (command is done)
TERMINAL_STATUSES = {
    CommandStatus.SUCCEEDED,
    CommandStatus.FAILED,
    CommandStatus.CANCELLED,
    CommandStatus.COMPLETED_WITH_ERRORS,
}


async def create_command(
    command_type: CommandType,
    *,
    initiated_by_ip: str | None = None,
    initiated_by_user: str | None = None,
    tag_filter: str | None = None,
    delay_minutes: int | None = None,
    delay_seconds: int | None = None,
    pause_minutes: int | None = None,
    dashboard_button_id: int | None = None,
) -> Command:
    """Create a new command with initial PENDING status."""
    return await Command.create(
        command_type=command_type,
        status=CommandStatus.PENDING,
        initiated_by_ip=initiated_by_ip,
        initiated_by_user=initiated_by_user,
        tag_filter=tag_filter,
        delay_minutes=delay_minutes,
        delay_seconds=delay_seconds,
        pause_minutes=pause_minutes,
        dashboard_button_id=dashboard_button_id,
    )


async def get_command(command_id: int) -> Command | None:
    return await Command.get_or_none(id=command_id)


async def list_commands(
    status: CommandStatus | None = None,
    limit: int | None = None,
) -> list[Command]:
    qs = Command.all().order_by("-created_at")
    if status is not None:
        qs = qs.filter(status=status)
    if limit is not None:
        qs = qs.limit(limit)
    return await qs


async def transition_status(command_id: int, new_status: CommandStatus) -> Command | None:
    """Transition a command to a new status, enforcing valid transitions.

    Records timestamps for each lifecycle stage.
    Raises ValueError if the transition is invalid.
    Returns None if the command doesn't exist.
    """
    cmd = await Command.get_or_none(id=command_id)
    if cmd is None:
        return None

    allowed = VALID_TRANSITIONS.get(cmd.status, set())
    if new_status not in allowed:
        raise ValueError(f"Invalid transition: {cmd.status} -> {new_status}")

    now = datetime.now(timezone.utc)
    cmd.status = new_status

    if new_status == CommandStatus.QUEUED:
        cmd.queued_at = now
    elif new_status == CommandStatus.RUNNING:
        cmd.started_at = now
    elif new_status in TERMINAL_STATUSES:
        cmd.completed_at = now

    await cmd.save()
    return cmd


async def cancel_command(command_id: int) -> bool:
    """Cancel a command. Returns True if cancelled, False if not found.

    Raises ValueError if the command is in a terminal status.
    """
    cmd = await Command.get_or_none(id=command_id)
    if cmd is None:
        return False

    if cmd.status not in CANCELLABLE_STATUSES:
        raise ValueError(f"Cannot cancel command in {cmd.status} status")

    await transition_status(command_id, CommandStatus.CANCELLED)
    return True


async def get_next_queued() -> Command | None:
    """Return the oldest queued command (FIFO)."""
    return await Command.filter(status=CommandStatus.QUEUED).order_by("created_at").first()


async def get_active_command() -> Command | None:
    """Return the currently running command, or None."""
    return await Command.filter(status=CommandStatus.RUNNING).first()


async def set_error_summary(command_id: int, message: str) -> Command | None:
    """Store error details on a command."""
    cmd = await Command.get_or_none(id=command_id)
    if cmd is None:
        return None
    cmd.error_summary = message
    await cmd.save()
    return cmd
