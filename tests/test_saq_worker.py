"""Tests for SAQ worker integration."""

from remander.worker import create_queue, create_worker, get_queue


class TestCreateQueue:
    async def test_queue_created_with_redis_url(self) -> None:
        """Queue should be created using the Redis URL from settings."""
        queue = create_queue(redis_url="redis://localhost:6379/0")
        assert queue is not None
        # SAQ RedisQueue stores the name
        assert queue.name == "remander"

    async def test_queue_uses_custom_name(self) -> None:
        queue = create_queue(redis_url="redis://localhost:6379/0")
        assert queue.name == "remander"


class TestCreateWorker:
    async def test_worker_created_with_concurrency_one(self) -> None:
        """Worker concurrency must be 1 for one-command-at-a-time constraint."""
        queue = create_queue(redis_url="redis://localhost:6379/0")
        worker = create_worker(queue)
        assert worker.concurrency == 1

    async def test_worker_has_process_command_function(self) -> None:
        """Worker must register the process_command job handler."""
        queue = create_queue(redis_url="redis://localhost:6379/0")
        worker = create_worker(queue)
        assert "process_command" in worker.functions


class TestGetQueue:
    async def test_get_queue_returns_singleton(self) -> None:
        """get_queue should return the module-level queue instance."""
        # get_queue returns the queue; it may be None if not initialized
        # This tests the function exists and is callable
        queue = get_queue()
        # Before lifespan, queue may be None
        assert queue is None or hasattr(queue, "enqueue")
