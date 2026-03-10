"""Tests for plugin KV data store."""

from remander.models.plugin_data import PluginData
from remander.plugins.data import delete_plugin_value, get_plugin_value, set_plugin_value


class TestPluginDataModel:
    async def test_create_plugin_data(self) -> None:
        record = await PluginData.create(
            plugin_name="hot_water",
            key="timer_state",
            value={"end_time": "2026-03-10T12:00:00"},
        )
        assert record.id is not None
        assert record.plugin_name == "hot_water"
        assert record.key == "timer_state"
        assert record.value == {"end_time": "2026-03-10T12:00:00"}

    async def test_unique_together_plugin_name_key(self) -> None:
        await PluginData.create(plugin_name="p1", key="k1", value={"v": 1})
        # Second create with same (plugin_name, key) should raise
        from tortoise.exceptions import IntegrityError

        try:
            await PluginData.create(plugin_name="p1", key="k1", value={"v": 2})
            assert False, "Expected IntegrityError"
        except IntegrityError:
            pass

    async def test_different_plugins_same_key(self) -> None:
        await PluginData.create(plugin_name="p1", key="k1", value={"v": 1})
        await PluginData.create(plugin_name="p2", key="k1", value={"v": 2})
        assert await PluginData.all().count() == 2


class TestPluginDataHelpers:
    async def test_set_and_get_value(self) -> None:
        await set_plugin_value("hot_water", "timer", {"minutes": 20})
        result = await get_plugin_value("hot_water", "timer")
        assert result == {"minutes": 20}

    async def test_get_missing_returns_none(self) -> None:
        result = await get_plugin_value("hot_water", "nonexistent")
        assert result is None

    async def test_get_missing_returns_default(self) -> None:
        result = await get_plugin_value("hot_water", "missing", default="fallback")
        assert result == "fallback"

    async def test_set_overwrites_existing(self) -> None:
        await set_plugin_value("hot_water", "timer", {"minutes": 20})
        await set_plugin_value("hot_water", "timer", {"minutes": 30})
        result = await get_plugin_value("hot_water", "timer")
        assert result == {"minutes": 30}

    async def test_delete_existing_key(self) -> None:
        await set_plugin_value("hot_water", "timer", {"minutes": 20})
        deleted = await delete_plugin_value("hot_water", "timer")
        assert deleted is True
        result = await get_plugin_value("hot_water", "timer")
        assert result is None

    async def test_delete_missing_key(self) -> None:
        deleted = await delete_plugin_value("hot_water", "nonexistent")
        assert deleted is False
