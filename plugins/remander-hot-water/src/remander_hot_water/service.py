"""Hot water service — business logic for pump timer control."""

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
    """Cancel the hot water timer — turn off pump and abort scheduled job."""
    state = await get_plugin_value(PLUGIN_NAME, TIMER_KEY)
    if state is None:
        return

    await sonoff_client.turn_off(settings.sonoff_ip)

    job_id = state.get("job_id")
    if job_id:
        job = await queue.job(job_id)
        if job:
            await queue.abort(job, error="Cancelled by user")

    await delete_plugin_value(PLUGIN_NAME, TIMER_KEY)
    logger.info("Hot water cancelled (job %s aborted)", job_id)


async def get_status() -> dict[str, Any]:
    """Get the current hot water timer status."""
    state = await get_plugin_value(PLUGIN_NAME, TIMER_KEY)
    if state is None:
        return {"active": False}

    end_time = datetime.fromisoformat(state["end_time"])
    remaining = (end_time - datetime.now(timezone.utc)).total_seconds()

    if remaining <= 0:
        # Timer has expired — clean up stale state
        await delete_plugin_value(PLUGIN_NAME, TIMER_KEY)
        return {"active": False}

    return {
        "active": True,
        "remaining_seconds": int(remaining),
        "duration_minutes": state["duration_minutes"],
        "end_time": state["end_time"],
    }
