"""Tests for AppConfig model and app_config service — TDD red/green approach."""

import pytest
from tortoise.exceptions import IntegrityError

from remander.models.app_config import AppConfig


class TestAppConfigModel:
    async def test_create_config_entry(self) -> None:
        # Values are stored as {"_v": ...} envelope — use integers/dicts/lists directly
        record = await AppConfig.create(key="nvr_port", value={"_v": 80})
        assert record.key == "nvr_port"
        assert record.value == {"_v": 80}
        assert record.updated_at is not None

    async def test_primary_key_is_key_field(self) -> None:
        await AppConfig.create(key="nvr_port", value={"_v": 80})
        fetched = await AppConfig.get(key="nvr_port")
        assert fetched.value == {"_v": 80}

    async def test_duplicate_key_raises(self) -> None:
        await AppConfig.create(key="smtp_host", value={"_v": "mail.example.com"})
        with pytest.raises(IntegrityError):
            await AppConfig.create(key="smtp_host", value={"_v": "other.example.com"})

    async def test_value_stores_various_types(self) -> None:
        await AppConfig.create(key="debug", value={"_v": True})
        await AppConfig.create(key="nvr_port", value={"_v": 8080})
        await AppConfig.create(key="latitude", value={"_v": 51.5})
        await AppConfig.create(key="available_durations", value={"_v": [15, 20, 30]})

        assert (await AppConfig.get(key="debug")).value == {"_v": True}
        assert (await AppConfig.get(key="nvr_port")).value == {"_v": 8080}
        assert (await AppConfig.get(key="latitude")).value == {"_v": 51.5}
        assert (await AppConfig.get(key="available_durations")).value == {"_v": [15, 20, 30]}

    async def test_plugin_key_namespace(self) -> None:
        await AppConfig.create(key="plugin.hot_water.sonoff_ip", value={"_v": "192.168.1.50"})
        record = await AppConfig.get(key="plugin.hot_water.sonoff_ip")
        assert record.value == {"_v": "192.168.1.50"}


class TestAppConfigService:
    async def test_get_config_value_existing(self) -> None:
        from remander.services.app_config import get_config_value, set_config_value

        await set_config_value("nvr_host", "10.0.0.1")
        result = await get_config_value("nvr_host")
        assert result == "10.0.0.1"

    async def test_get_config_value_missing_returns_none(self) -> None:
        from remander.services.app_config import get_config_value

        result = await get_config_value("nonexistent_key")
        assert result is None

    async def test_get_config_value_missing_returns_default(self) -> None:
        from remander.services.app_config import get_config_value

        result = await get_config_value("nonexistent_key", default="fallback")
        assert result == "fallback"

    async def test_set_config_value_creates_new(self) -> None:
        from remander.services.app_config import get_config_value, set_config_value

        await set_config_value("smtp_port", 587)
        assert await get_config_value("smtp_port") == 587

    async def test_set_config_value_upserts(self) -> None:
        from remander.services.app_config import get_config_value, set_config_value

        await set_config_value("nvr_port", 80)
        await set_config_value("nvr_port", 8080)
        assert await get_config_value("nvr_port") == 8080

    async def test_delete_config_value_existing(self) -> None:
        from remander.services.app_config import (
            delete_config_value,
            get_config_value,
            set_config_value,
        )

        await set_config_value("smtp_host", "mail.example.com")
        deleted = await delete_config_value("smtp_host")
        assert deleted is True
        assert await get_config_value("smtp_host") is None

    async def test_delete_config_value_missing(self) -> None:
        from remander.services.app_config import delete_config_value

        deleted = await delete_config_value("nonexistent_key")
        assert deleted is False

    async def test_get_all_core_settings(self) -> None:
        from remander.services.app_config import get_all_config, set_config_value

        await set_config_value("nvr_host", "10.0.0.1")
        await set_config_value("nvr_port", 80)
        await set_config_value("plugin.hot_water.sonoff_ip", "192.168.1.50")

        core = await get_all_config(prefix=None)
        assert "nvr_host" in core
        assert "nvr_port" in core
        # Plugin keys should NOT appear in core config
        assert "plugin.hot_water.sonoff_ip" not in core

    async def test_get_all_plugin_settings(self) -> None:
        from remander.services.app_config import get_all_config, set_config_value

        await set_config_value("plugin.hot_water.sonoff_ip", "192.168.1.50")
        await set_config_value("plugin.hot_water.default_duration", 20)
        await set_config_value("nvr_host", "10.0.0.1")

        plugin = await get_all_config(prefix="plugin.")
        assert "plugin.hot_water.sonoff_ip" in plugin
        assert "plugin.hot_water.default_duration" in plugin
        # Core keys should NOT appear
        assert "nvr_host" not in plugin


class TestSettingsCache:
    async def test_get_settings_returns_settings_instance(self) -> None:
        from remander.config import Settings, get_settings

        s = get_settings()
        assert isinstance(s, Settings)

    async def test_set_and_get_settings(self) -> None:
        from remander.config import Settings, get_settings, set_settings

        original = get_settings()
        custom = Settings(
            nvr_host="custom-host",
            nvr_username="user",
            nvr_password="pass",
        )
        set_settings(custom)
        assert get_settings().nvr_host == "custom-host"
        # Restore original
        set_settings(original)

    async def test_load_core_config_merges_db_over_env(self) -> None:
        """DB values overlay env-sourced Settings fields."""
        from remander.config import get_settings
        from remander.services.app_config import load_core_config, set_config_value

        # Store a different nvr_port than the default (80)
        await set_config_value("nvr_port", 9090)
        await load_core_config()

        s = get_settings()
        assert s.nvr_port == 9090

    async def test_load_core_config_skips_plugin_keys(self) -> None:
        """Plugin-namespaced keys are not applied to core Settings."""
        from remander.config import get_settings
        from remander.services.app_config import load_core_config, set_config_value

        original_host = get_settings().nvr_host
        await set_config_value("plugin.hot_water.sonoff_ip", "1.2.3.4")
        await load_core_config()

        # nvr_host unchanged, and no error about unexpected field
        assert get_settings().nvr_host == original_host

    async def test_load_core_config_ignores_unknown_keys(self) -> None:
        """Unknown DB keys (from old settings) do not raise errors."""
        from remander.services.app_config import load_core_config, set_config_value

        await set_config_value("old_removed_setting", "value")
        # Should not raise
        await load_core_config()


class TestPluginSettingsCache:
    async def test_set_and_get_plugin_setting(self) -> None:
        from remander.services.app_config import (
            get_plugin_setting,
            load_plugin_config,
            set_plugin_setting,
        )

        await set_plugin_setting("hot_water", "sonoff_ip", "192.168.1.50")
        await load_plugin_config()
        result = get_plugin_setting("hot_water", "sonoff_ip")
        assert result == "192.168.1.50"

    async def test_get_plugin_setting_missing_returns_default(self) -> None:
        from remander.services.app_config import get_plugin_setting, load_plugin_config

        await load_plugin_config()
        result = get_plugin_setting("hot_water", "nonexistent", default="fallback")
        assert result == "fallback"

    async def test_set_plugin_setting_refreshes_cache(self) -> None:
        from remander.services.app_config import get_plugin_setting, set_plugin_setting

        await set_plugin_setting("hot_water", "sonoff_ip", "10.0.0.50")
        # get_plugin_setting reads from the in-memory cache, which set_plugin_setting refreshes
        assert get_plugin_setting("hot_water", "sonoff_ip") == "10.0.0.50"

    async def test_multiple_plugins_isolated(self) -> None:
        from remander.services.app_config import (
            get_plugin_setting,
            load_plugin_config,
            set_plugin_setting,
        )

        await set_plugin_setting("hot_water", "ip", "1.1.1.1")
        await set_plugin_setting("other_plugin", "ip", "2.2.2.2")
        await load_plugin_config()

        assert get_plugin_setting("hot_water", "ip") == "1.1.1.1"
        assert get_plugin_setting("other_plugin", "ip") == "2.2.2.2"


class TestCustomColors:
    async def test_get_custom_colors_empty_by_default(self) -> None:
        from remander.services.app_config import get_custom_colors

        colors = await get_custom_colors()
        assert colors == []

    async def test_add_custom_color(self) -> None:
        from remander.services.app_config import add_custom_color, get_custom_colors

        await add_custom_color("#AABBCC")
        colors = await get_custom_colors()
        assert "#AABBCC" in colors

    async def test_add_same_color_twice_deduplicates(self) -> None:
        from remander.services.app_config import add_custom_color, get_custom_colors

        await add_custom_color("#AABBCC")
        await add_custom_color("#AABBCC")
        colors = await get_custom_colors()
        assert colors.count("#AABBCC") == 1

    async def test_most_recently_added_is_first(self) -> None:
        from remander.services.app_config import add_custom_color, get_custom_colors

        await add_custom_color("#111111")
        await add_custom_color("#222222")
        colors = await get_custom_colors()
        assert colors[0] == "#222222"

    async def test_re_adding_existing_moves_it_to_front(self) -> None:
        from remander.services.app_config import add_custom_color, get_custom_colors

        await add_custom_color("#111111")
        await add_custom_color("#222222")
        await add_custom_color("#111111")  # re-add; should bubble to front
        colors = await get_custom_colors()
        assert colors[0] == "#111111"

    async def test_remove_custom_color(self) -> None:
        from remander.services.app_config import (
            add_custom_color,
            get_custom_colors,
            remove_custom_color,
        )

        await add_custom_color("#AABBCC")
        await remove_custom_color("#AABBCC")
        colors = await get_custom_colors()
        assert "#AABBCC" not in colors

    async def test_remove_nonexistent_color_is_noop(self) -> None:
        from remander.services.app_config import get_custom_colors, remove_custom_color

        await remove_custom_color("#FFFFFF")  # should not raise
        assert await get_custom_colors() == []

    async def test_capped_at_max_custom_colors(self) -> None:
        from remander.services.app_config import MAX_CUSTOM_COLORS, add_custom_color, get_custom_colors

        for i in range(MAX_CUSTOM_COLORS + 5):
            await add_custom_color(f"#{i:06X}")
        colors = await get_custom_colors()
        assert len(colors) == MAX_CUSTOM_COLORS
