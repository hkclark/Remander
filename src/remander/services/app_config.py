"""AppConfig service — CRUD helpers, settings cache overlay, and plugin config cache."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# In-memory plugin config cache: {"hot_water": {"sonoff_ip": "...", ...}, ...}
_plugin_config: dict[str, dict[str, Any]] = {}


# ── Low-level CRUD ────────────────────────────────────────────────────────────


async def get_config_value(key: str, *, default: Any = None) -> Any:
    """Read a single value from AppConfig. Returns `default` if not found."""
    from remander.models.app_config import AppConfig

    record = await AppConfig.get_or_none(key=key)
    if record is None:
        return default
    # Values are stored wrapped in {"_v": ...} to support scalar types (str, int, etc.)
    # because Tortoise JSONField treats plain Python str as pre-encoded JSON.
    return record.value["_v"]


async def set_config_value(key: str, value: Any) -> None:
    """Upsert a single value in AppConfig."""
    from remander.models.app_config import AppConfig

    # Wrap to handle scalar types — see get_config_value note above
    await AppConfig.update_or_create(defaults={"value": {"_v": value}}, key=key)


async def delete_config_value(key: str) -> bool:
    """Delete a value from AppConfig. Returns True if deleted, False if not found."""
    from remander.models.app_config import AppConfig

    deleted_count = await AppConfig.filter(key=key).delete()
    return deleted_count > 0


async def get_all_config(*, prefix: str | None) -> dict[str, Any]:
    """Return all AppConfig entries, optionally filtered by key prefix.

    - ``prefix=None`` returns only keys without a dot-namespace prefix
      (i.e., core settings, excluding plugin.* keys).
    - ``prefix="plugin."`` returns only plugin-namespaced keys.
    """
    from remander.models.app_config import AppConfig

    all_records = await AppConfig.all()
    result: dict[str, Any] = {}
    for record in all_records:
        unwrapped = record.value["_v"]
        if prefix is None:
            if not record.key.startswith("plugin."):
                result[record.key] = unwrapped
        else:
            if record.key.startswith(prefix):
                result[record.key] = unwrapped
    return result


# ── Core settings cache overlay ───────────────────────────────────────────────


async def load_core_config() -> None:
    """Load core settings from AppConfig and merge over the .env-based Settings.

    Only known Settings fields are applied — unknown keys are silently ignored
    so that old/removed settings in the DB don't cause errors.
    """
    from remander.config import Settings, set_settings

    # Start fresh from .env / env vars
    base = Settings()  # type: ignore[call-arg]
    base_dict = base.model_dump()

    overrides = await get_all_config(prefix=None)
    merged = {**base_dict}
    for key, value in overrides.items():
        if key in base_dict:
            merged[key] = value
        else:
            logger.debug("Ignoring unknown AppConfig key: %s", key)

    new_settings = Settings.model_validate(merged)
    set_settings(new_settings)
    logger.info("Core settings reloaded (%d DB overrides):", len(overrides))
    for key, value in sorted(new_settings.model_dump().items()):
        logger.info("  %s = %r", key, value)


# ── Plugin settings cache ─────────────────────────────────────────────────────


async def load_plugin_config() -> None:
    """Load plugin settings from AppConfig into the in-memory cache.

    Called during lifespan after core config is loaded. Also called by
    set_plugin_setting() to keep the cache fresh after each write.
    """
    global _plugin_config
    plugin_rows = await get_all_config(prefix="plugin.")
    new_cache: dict[str, dict[str, Any]] = {}
    for full_key, value in plugin_rows.items():
        # full_key format: "plugin.{name}.{field}"
        parts = full_key.split(".", 2)
        if len(parts) == 3:
            _, plugin_name, field = parts
            new_cache.setdefault(plugin_name, {})[field] = value
    _plugin_config = new_cache
    if new_cache:
        logger.info("Plugin settings reloaded:")
        for plugin_name, settings in sorted(new_cache.items()):
            for key, value in sorted(settings.items()):
                logger.info("  plugin.%s.%s = %r", plugin_name, key, value)
    else:
        logger.info("Plugin settings reloaded: (none in DB)")


def get_plugin_setting(plugin_name: str, key: str, *, default: Any = None) -> Any:
    """Read a plugin setting from the in-memory cache (sync).

    Call ``load_plugin_config()`` during lifespan before using this.
    """
    return _plugin_config.get(plugin_name, {}).get(key, default)


async def set_plugin_setting(plugin_name: str, key: str, value: Any) -> None:
    """Write a plugin setting to AppConfig and refresh the in-memory cache."""
    full_key = f"plugin.{plugin_name}.{key}"
    await set_config_value(full_key, value)
    await load_plugin_config()
