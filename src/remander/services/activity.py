"""Activity logging service — per-step, per-device execution records."""

from remander.models.activity import ActivityLog
from remander.models.enums import ActivityStatus


async def log_activity(
    command_id: int,
    step_name: str,
    status: ActivityStatus,
    *,
    device_id: int | None = None,
    detail: str | None = None,
    duration_ms: int | None = None,
) -> ActivityLog:
    """Create an activity log entry."""
    return await ActivityLog.create(
        command_id=command_id,
        device_id=device_id,
        step_name=step_name,
        status=status,
        detail=detail,
        duration_ms=duration_ms,
    )


async def get_activities_for_command(command_id: int) -> list[ActivityLog]:
    """List all activity log entries for a command, ordered by created_at."""
    return await ActivityLog.filter(command_id=command_id).order_by("created_at")


async def get_activities_for_device(device_id: int) -> list[ActivityLog]:
    """List all activity log entries for a device across commands."""
    return await ActivityLog.filter(device_id=device_id).order_by("created_at")


async def update_activity_status(
    activity_id: int,
    status: ActivityStatus,
    *,
    duration_ms: int | None = None,
    detail: str | None = None,
) -> ActivityLog | None:
    """Update an activity log entry's status, duration, and/or detail."""
    entry = await ActivityLog.get_or_none(id=activity_id)
    if entry is None:
        return None
    entry.status = status
    if duration_ms is not None:
        entry.duration_ms = duration_ms
    if detail is not None:
        entry.detail = detail
    await entry.save()
    return entry
