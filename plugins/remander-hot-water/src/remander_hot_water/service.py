"""Hot water service — business logic for pump timer control."""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from remander.clients.sonoff import SonoffClient
from remander.plugins.data import delete_plugin_value, get_plugin_value, set_plugin_value
from remander_hot_water.settings import HotWaterSettings

logger = logging.getLogger(__name__)

PLUGIN_NAME = "hot_water"
TIMER_KEY = "timer_state"
DEVICE_QUERY_TIMEOUT = 2.0  # seconds — keep well under the HTMX 5s poll interval


async def start_hot_water(
    *,
    settings: HotWaterSettings,
    sonoff_client: SonoffClient,
    queue: Any,
    duration_minutes: int,
) -> None:
    """Turn on the hot water pump and schedule automatic turn-off."""
    await sonoff_client.turn_on(settings.sonoff_ip)

    # Schedule the turn-off SAQ job — SAQ expects a Unix timestamp, not a datetime
    delay_seconds = duration_minutes * 60
    job = await queue.enqueue(
        "turn_off_hot_water",
        scheduled=int(time.time()) + delay_seconds,
        timeout=delay_seconds + 30,
    )

    end_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    await set_plugin_value(
        PLUGIN_NAME,
        TIMER_KEY,
        {
            "end_time": end_time.isoformat(),
            "duration_minutes": duration_minutes,
            "job_id": job.id,
        },
    )

    logger.info("Hot water started for %d minutes (job %s)", duration_minutes, job.id)


async def cancel_hot_water(
    *,
    settings: HotWaterSettings,
    sonoff_client: SonoffClient,
    queue: Any,
) -> None:
    """Turn off the pump and abort any scheduled job.

    Always turns off the device — handles both timer-managed and externally-started pumps.
    """
    await sonoff_client.turn_off(settings.sonoff_ip)

    state = await get_plugin_value(PLUGIN_NAME, TIMER_KEY)
    if state is not None:
        job_id = state.get("job_id")
        if job_id:
            job = await queue.job(job_id)
            if job:
                await queue.abort(job, error="Cancelled by user")
        await delete_plugin_value(PLUGIN_NAME, TIMER_KEY)
        logger.info("Hot water cancelled (job %s aborted)", job_id)
    else:
        logger.info("Hot water turned off (no managed timer)")


async def _query_device_state(settings: HotWaterSettings, sonoff_client: SonoffClient) -> str:
    """Query the Sonoff device state with a short timeout.

    Returns "on", "off", "unreachable", or "error".
    """
    try:
        is_on = await asyncio.wait_for(
            sonoff_client.is_on(settings.sonoff_ip),
            timeout=DEVICE_QUERY_TIMEOUT,
        )
        return "on" if is_on else "off"
    except asyncio.TimeoutError:
        logger.warning("Hot water device at %s timed out", settings.sonoff_ip)
        return "unreachable"
    except Exception:
        logger.warning("Hot water device at %s returned an error", settings.sonoff_ip)
        return "error"


async def get_status(
    *,
    settings: HotWaterSettings,
    sonoff_client: SonoffClient,
) -> dict[str, Any]:
    """Get the current hot water status — timer state plus live device state."""
    timer_state = await get_plugin_value(PLUGIN_NAME, TIMER_KEY)
    device_state = await _query_device_state(settings, sonoff_client)

    # Check whether our timer is still active
    if timer_state is not None:
        end_time = datetime.fromisoformat(timer_state["end_time"])
        remaining = (end_time - datetime.now(timezone.utc)).total_seconds()

        if remaining > 0:
            return {
                "active": True,
                "device_state": device_state,
                "remaining_seconds": int(remaining),
                "duration_minutes": timer_state["duration_minutes"],
                "end_time": timer_state["end_time"],
            }

        # Timer has expired — clean up stale state
        await delete_plugin_value(PLUGIN_NAME, TIMER_KEY)

    return {
        "active": False,
        "device_state": device_state,
    }
