"""Delayed command and re-arm scheduling via SAQ."""

import logging
import time

from remander.models.command import Command
from remander.models.enums import CommandType
from remander.worker import get_queue

logger = logging.getLogger(__name__)

# Pause command types that can have re-arm timers
_PAUSE_COMMAND_TYPES = {CommandType.PAUSE_NOTIFICATIONS, CommandType.PAUSE_RECORDING}


async def schedule_delayed_command(command_id: int, delay_minutes: int) -> None:
    """Enqueue a SAQ job to process a command after delay_minutes.

    Stores the SAQ job key on the command for later cancellation.
    """
    from remander.config import get_settings

    queue = get_queue()
    if queue is None:
        logger.warning("No queue available; cannot schedule delayed command %d", command_id)
        return

    scheduled = int(time.time()) + delay_minutes * 60
    timeout = get_settings().job_timeout_seconds
    job = await queue.enqueue("process_command", command_id=command_id, scheduled=scheduled, timeout=timeout)
    cmd = await Command.get(id=command_id)
    cmd.saq_job_id = job.key
    await cmd.save()


async def cancel_delayed_command(command_id: int) -> None:
    """Cancel a previously scheduled delayed command."""
    cmd = await Command.get(id=command_id)
    if not cmd.saq_job_id:
        return

    queue = get_queue()
    if queue is not None:
        await queue.abort(cmd.saq_job_id, "cancelled")

    cmd.saq_job_id = None
    await cmd.save()


async def schedule_rearm(command_id: int, pause_minutes: int) -> None:
    """Schedule a re-arm job to restore bitmasks after pause_minutes.

    Stores the SAQ job key on the originating command for later cancellation.
    """
    from remander.config import get_settings

    queue = get_queue()
    if queue is None:
        logger.warning("No queue available; cannot schedule re-arm for command %d", command_id)
        return

    scheduled = int(time.time()) + pause_minutes * 60
    timeout = get_settings().job_timeout_seconds
    job = await queue.enqueue("process_rearm", command_id=command_id, scheduled=scheduled, timeout=timeout)
    cmd = await Command.get(id=command_id)
    cmd.saq_job_id = job.key
    await cmd.save()


async def cancel_pending_rearms() -> None:
    """Cancel all pending re-arm timer jobs.

    Called when a full Set Home or Set Away command runs, invalidating any
    outstanding pause timers.
    """
    # Find pause commands with active re-arm job IDs
    rearm_commands = await Command.filter(
        command_type__in=[ct.value for ct in _PAUSE_COMMAND_TYPES],
        saq_job_id__not_isnull=True,
    )

    queue = get_queue()
    for cmd in rearm_commands:
        if not cmd.saq_job_id:
            continue
        if queue is not None:
            await queue.abort(cmd.saq_job_id, "superseded")
            logger.info("Cancelled re-arm job %s for command %d", cmd.saq_job_id, cmd.id)
        cmd.saq_job_id = None
        await cmd.save()
