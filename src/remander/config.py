"""Application configuration via pydantic-settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Reason: Pydantic model for settings validation and .env loading
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Reolink NVR — no defaults required; can be configured via Admin → Settings
    nvr_host: str = ""
    nvr_port: int = 80
    nvr_username: str = ""
    nvr_password: SecretStr = SecretStr("")
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

    # Debug mode
    debug: bool = False

    # Logging
    log_dir: str = "./logs"
    log_level: str = "INFO"
    workflow_debug: bool = False

    # Docker user/group
    puid: int = 1000
    pgid: int = 1000

    # Power-on timing
    power_on_timeout_seconds: int = 120
    power_on_poll_interval_seconds: int = 10

    # SAQ job timeout — NVR operations can take many seconds; 10s SAQ default is too short
    job_timeout_seconds: int = 120

    # Guest dashboard
    guest_dashboard_show_mode: bool = True
    guest_dashboard_pin: str = "5555"

    # Authentication
    session_secret_key: str = ""
    password_reset_expiry_seconds: int = 3600
    invitation_expiry_seconds: int = 604800


_cached_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached Settings instance, creating it fresh if not yet cached."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()  # type: ignore[call-arg]
    return _cached_settings


def set_settings(settings: Settings) -> None:
    """Replace the cached Settings instance (used by lifespan and tests)."""
    global _cached_settings
    _cached_settings = settings
