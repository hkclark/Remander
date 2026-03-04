"""SAQ worker setup — Redis-backed job queue for command processing."""

import logging

from saq import Queue, Worker
from saq.types import Context

logger = logging.getLogger(__name__)

# Module-level queue instance, initialized during lifespan
_queue: Queue | None = None


def create_queue(redis_url: str) -> Queue:
    """Create a SAQ queue backed by Redis."""
    return Queue.from_url(redis_url, name="remander")


async def process_command(ctx: Context, command_id: int) -> None:
    """SAQ job handler: process a queued command by running its workflow."""
    from remander.services.queue import execute_command

    logger.info("Processing command %d", command_id)
    await execute_command(command_id)


async def process_rearm(ctx: Context, command_id: int) -> None:
    """SAQ job handler: run the re-arm workflow to restore saved bitmasks."""
    from remander.services.queue import execute_rearm

    logger.info("Processing re-arm for command %d", command_id)
    await execute_rearm(command_id)


def create_worker(queue: Queue) -> Worker:
    """Create a SAQ worker with concurrency=1 (one command at a time)."""
    return Worker(
        queue=queue,
        functions=[
            ("process_command", process_command),
            ("process_rearm", process_rearm),
        ],
        concurrency=1,
    )


def get_queue() -> Queue | None:
    """Return the module-level queue instance (None before lifespan init)."""
    return _queue


def set_queue(queue: Queue) -> None:
    """Set the module-level queue instance (called during lifespan)."""
    global _queue
    _queue = queue
