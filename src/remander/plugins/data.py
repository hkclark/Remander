"""Async CRUD helpers for the plugin KV data store."""

from typing import Any

from remander.models.plugin_data import PluginData


async def get_plugin_value(plugin_name: str, key: str, *, default: Any = None) -> Any:
    """Get a value from the plugin data store, returning default if not found."""
    record = await PluginData.get_or_none(plugin_name=plugin_name, key=key)
    if record is None:
        return default
    return record.value


async def set_plugin_value(plugin_name: str, key: str, value: Any) -> None:
    """Set a value in the plugin data store (upsert)."""
    record = await PluginData.get_or_none(plugin_name=plugin_name, key=key)
    if record is None:
        await PluginData.create(plugin_name=plugin_name, key=key, value=value)
    else:
        record.value = value
        await record.save()


async def delete_plugin_value(plugin_name: str, key: str) -> bool:
    """Delete a value from the plugin data store. Returns True if deleted."""
    deleted_count = await PluginData.filter(plugin_name=plugin_name, key=key).delete()
    return deleted_count > 0
