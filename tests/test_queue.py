"""Tests for command queueing — SAQ timeout calculation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from remander.config import Settings


class TestEnqueueCommandTimeout:
    async def test_saq_timeout_combines_power_on_and_job_overhead(self) -> None:
        """SAQ job timeout must be power_on_timeout + job_overhead so the job is never
        cancelled while WaitForPowerOnNode is still polling."""
        from remander.services.queue import enqueue_command

        settings = Settings(
            power_on_timeout_seconds=90,
            job_timeout_seconds=60,
            session_secret_key="test",
        )
        mock_queue = AsyncMock()

        with (
            patch("remander.services.queue.get_queue", return_value=mock_queue),
            patch("remander.config.get_settings", return_value=settings),
            patch("remander.services.queue.transition_status", new_callable=AsyncMock),
        ):
            await enqueue_command(1)

        mock_queue.enqueue.assert_awaited_once()
        kwargs = mock_queue.enqueue.call_args.kwargs
        assert kwargs["timeout"] == 150  # 90 + 60

    async def test_saq_timeout_scales_with_power_on_timeout(self) -> None:
        """If power_on_timeout_seconds is increased, the SAQ timeout increases proportionally."""
        from remander.services.queue import enqueue_command

        settings = Settings(
            power_on_timeout_seconds=300,
            job_timeout_seconds=60,
            session_secret_key="test",
        )
        mock_queue = AsyncMock()

        with (
            patch("remander.services.queue.get_queue", return_value=mock_queue),
            patch("remander.config.get_settings", return_value=settings),
            patch("remander.services.queue.transition_status", new_callable=AsyncMock),
        ):
            await enqueue_command(1)

        kwargs = mock_queue.enqueue.call_args.kwargs
        assert kwargs["timeout"] == 360  # 300 + 60
