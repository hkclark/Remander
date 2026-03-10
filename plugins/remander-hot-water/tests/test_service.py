"""Tests for hot water service — TDD red/green approach."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from remander_hot_water.service import (
    cancel_hot_water,
    get_status,
    start_hot_water,
)
from remander_hot_water.settings import HotWaterSettings


@pytest.fixture
def settings() -> HotWaterSettings:
    return HotWaterSettings(sonoff_ip="192.168.1.99")


@pytest.fixture
def mock_sonoff() -> AsyncMock:
    client = AsyncMock()
    client.turn_on = AsyncMock()
    client.turn_off = AsyncMock()
    return client


@pytest.fixture
def mock_queue() -> MagicMock:
    queue = MagicMock()
    queue.enqueue = AsyncMock(return_value=MagicMock(id="job-123"))
    queue.job = AsyncMock(return_value=MagicMock())
    queue.abort = AsyncMock()
    return queue


class TestStartHotWater:
    async def test_turns_on_sonoff_device(self, settings, mock_sonoff, mock_queue) -> None:
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        mock_sonoff.turn_on.assert_awaited_once_with("192.168.1.99")

    async def test_schedules_turn_off_job(self, settings, mock_sonoff, mock_queue) -> None:
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        mock_queue.enqueue.assert_awaited_once()
        call_kwargs = mock_queue.enqueue.call_args
        assert call_kwargs[0][0] == "turn_off_hot_water"
        assert call_kwargs[1]["timeout"] == 20 * 60 + 30

    async def test_stores_timer_state(self, settings, mock_sonoff, mock_queue) -> None:
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=15,
        )
        from remander.plugins.data import get_plugin_value

        state = await get_plugin_value("hot_water", "timer_state")
        assert state is not None
        assert state["duration_minutes"] == 15
        assert "end_time" in state
        assert "job_id" in state


class TestCancelHotWater:
    async def test_turns_off_sonoff_device(self, settings, mock_sonoff, mock_queue) -> None:
        # Start first so there's state to cancel
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        await cancel_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
        )
        mock_sonoff.turn_off.assert_awaited_once_with("192.168.1.99")

    async def test_aborts_scheduled_job(self, settings, mock_sonoff, mock_queue) -> None:
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        await cancel_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
        )
        mock_queue.abort.assert_awaited_once()

    async def test_clears_timer_state(self, settings, mock_sonoff, mock_queue) -> None:
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        await cancel_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
        )
        from remander.plugins.data import get_plugin_value

        state = await get_plugin_value("hot_water", "timer_state")
        assert state is None

    async def test_cancel_when_not_active_is_safe(self, settings, mock_sonoff, mock_queue) -> None:
        """Cancelling when there's no active timer should not raise."""
        await cancel_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
        )
        mock_sonoff.turn_off.assert_not_awaited()


class TestGetStatus:
    async def test_inactive_when_no_timer(self) -> None:
        status = await get_status()
        assert status["active"] is False

    async def test_active_with_remaining_time(self, settings, mock_sonoff, mock_queue) -> None:
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        status = await get_status()
        assert status["active"] is True
        assert status["remaining_seconds"] > 0
        assert status["duration_minutes"] == 20

    async def test_expired_timer_returns_inactive(self) -> None:
        """If the timer has expired (end_time in the past), status should be inactive."""
        from remander.plugins.data import set_plugin_value

        past_time = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        await set_plugin_value(
            "hot_water",
            "timer_state",
            {"end_time": past_time, "duration_minutes": 20, "job_id": "old"},
        )
        status = await get_status()
        assert status["active"] is False
