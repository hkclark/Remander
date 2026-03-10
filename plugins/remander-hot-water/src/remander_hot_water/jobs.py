"""SAQ job handlers for the hot water plugin."""

import logging

from saq.types import Context

from remander.clients.sonoff import SonoffClient
from remander.plugins.data import delete_plugin_value
from remander_hot_water.settings import HotWaterSettings

logger = logging.getLogger(__name__)


async def turn_off_hot_water(ctx: Context) -> None:
    """SAQ job: turn off the hot water pump after the timer expires."""
    settings = HotWaterSettings()
    client = SonoffClient()
    await client.turn_off(settings.sonoff_ip)
    await delete_plugin_value("hot_water", "timer_state")
    logger.info("Hot water auto-off completed (IP: %s)", settings.sonoff_ip)
