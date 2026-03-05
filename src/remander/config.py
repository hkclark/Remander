"""Application configuration via pydantic-settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Reason: Pydantic model for settings validation and .env loading
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Reolink NVR
    nvr_host: str
    nvr_port: int = 80
    nvr_username: str
    nvr_password: SecretStr
    nvr_use_https: bool = False
    nvr_timeout: int = 15
    nvr_debug: str = "false"
    nvr_debug_max_length: int = 0

    # Redis (SAQ job queue)
    redis_url: str = "redis://redis:6379/0"

    # Database
    database_url: str = "sqlite:///app/data/remander.db"

    # Email notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_use_tls: bool = True

    # Location (sunrise/sunset)
    latitude: float = 0.0
    longitude: float = 0.0

    # Logging
    log_dir: str = "./logs"
    log_level: str = "INFO"

    # Docker user/group
    puid: int = 1000
    pgid: int = 1000

    # Power-on timing
    power_on_timeout_seconds: int = 120
    power_on_poll_interval_seconds: int = 10


def get_settings() -> Settings:
    """Create and return a Settings instance."""
    return Settings()  # type: ignore[call-arg]
