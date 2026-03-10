# Reason: Pydantic model for settings validation and env loading
"""Hot water plugin configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class HotWaterSettings(BaseSettings):
    """Configuration for the hot water recirculation pump plugin.

    All settings are loaded from env vars prefixed with PLUGIN_HOT_WATER_.
    """

    model_config = SettingsConfigDict(env_prefix="PLUGIN_HOT_WATER_")

    sonoff_ip: str = "192.168.1.50"
    default_duration_minutes: int = 20
    available_durations: list[int] = [15, 20, 30]
