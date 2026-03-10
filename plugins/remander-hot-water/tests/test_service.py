"""Tests for hot water service — TDD red/green approach."""

import asyncio
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
    client.is_on = AsyncMock(return_value=False)
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

    async def test_cancel_without_timer_still_turns_off(
        self, settings, mock_sonoff, mock_queue
    ) -> None:
        """Cancelling without a timer (e.g. externally started) still turns off the device."""
        await cancel_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
        )
        mock_sonoff.turn_off.assert_awaited_once_with("192.168.1.99")
        mock_queue.abort.assert_not_awaited()


class TestGetStatus:
    async def test_device_off_no_timer(self, settings, mock_sonoff) -> None:
        mock_sonoff.is_on.return_value = False
        status = await get_status(settings=settings, sonoff_client=mock_sonoff)
        assert status["active"] is False
        assert status["device_state"] == "off"

    async def test_active_timer_with_device_on(
        self, settings, mock_sonoff, mock_queue
    ) -> None:
        mock_sonoff.is_on.return_value = True
        await start_hot_water(
            settings=settings,
            sonoff_client=mock_sonoff,
            queue=mock_queue,
            duration_minutes=20,
        )
        status = await get_status(settings=settings, sonoff_client=mock_sonoff)
        assert status["active"] is True
        assert status["device_state"] == "on"
        assert status["remaining_seconds"] > 0
        assert status["duration_minutes"] == 20

    async def test_device_on_externally_no_timer(self, settings, mock_sonoff) -> None:
        """Device is on but we have no timer — started by another system."""
        mock_sonoff.is_on.return_value = True
        status = await get_status(settings=settings, sonoff_client=mock_sonoff)
        assert status["active"] is False
        assert status["device_state"] == "on"

    async def test_device_unreachable(self, settings, mock_sonoff) -> None:
        mock_sonoff.is_on.side_effect = asyncio.TimeoutError()
        status = await get_status(settings=settings, sonoff_client=mock_sonoff)
        assert status["active"] is False
        assert status["device_state"] == "unreachable"

    async def test_device_error(self, settings, mock_sonoff) -> None:
        mock_sonoff.is_on.side_effect = Exception("connection refused")
        status = await get_status(settings=settings, sonoff_client=mock_sonoff)
        assert status["active"] is False
        assert status["device_state"] == "error"

    async def test_expired_timer_clears_state(self, settings, mock_sonoff) -> None:
        mock_sonoff.is_on.return_value = False
        from remander.plugins.data import set_plugin_value

        past_time = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        await set_plugin_value(
            "hot_water",
            "timer_state",
            {"end_time": past_time, "duration_minutes": 20, "job_id": "old"},
        )
        status = await get_status(settings=settings, sonoff_client=mock_sonoff)
        assert status["active"] is False
