"""SAQ worker setup — Redis-backed job queue for command processing."""

import logging
from collections.abc import Callable

from saq import Queue, Worker
from saq.types import Context


class EmbeddedWorker(Worker):
    """SAQ worker that doesn't install its own signal handlers.

    When running inside uvicorn, signal handling is owned by uvicorn — it translates
    SIGINT/SIGTERM into lifespan shutdown, which calls worker.stop(). If SAQ also
    installs SIGINT/SIGTERM handlers, it steals the signal from uvicorn, causing
    the app to hang until multiple Ctrl+C presses force-kill it.
    """

    SIGNALS: list = []


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


def create_worker(
    queue: Queue,
    extra_functions: list[tuple[str, Callable]] | None = None,
) -> EmbeddedWorker:
    """Create a SAQ worker with concurrency=1 (one command at a time)."""
    functions: list[tuple[str, Callable]] = [
        ("process_command", process_command),
        ("process_rearm", process_rearm),
    ]
    if extra_functions:
        functions.extend(extra_functions)
    return EmbeddedWorker(
        queue=queue,
        functions=functions,
        concurrency=1,
    )


def get_queue() -> Queue | None:
    """Return the module-level queue instance (None before lifespan init)."""
    return _queue


def set_queue(queue: Queue) -> None:
    """Set the module-level queue instance (called during lifespan)."""
    global _queue
    _queue = queue
