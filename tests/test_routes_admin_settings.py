"""Tests for admin settings routes — TDD red/green approach."""

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _setup_plugin_registry():
    """Register the hot water plugin for settings tests."""
    from remander_hot_water.plugin import HotWaterPlugin

    from remander.plugins.registry import PluginRegistry, set_registry

    registry = PluginRegistry()
    registry.register(HotWaterPlugin())
    set_registry(registry)
    yield
    set_registry(None)


class TestSettingsPage:
    async def test_get_settings_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/admin/settings")
        assert response.status_code == 200

    async def test_settings_page_contains_nvr_group(self, client: AsyncClient) -> None:
        response = await client.get("/admin/settings")
        assert "NVR" in response.text

    async def test_settings_page_contains_email_group(self, client: AsyncClient) -> None:
        response = await client.get("/admin/settings")
        assert "Email" in response.text

    async def test_settings_page_contains_readonly_section(self, client: AsyncClient) -> None:
        response = await client.get("/admin/settings")
        assert "database_url" in response.text or "Database URL" in response.text


class TestSaveCoreSettings:
    async def test_save_nvr_group_persists_values(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/core/nvr",
            data={
                "nvr_host": "10.0.0.1",
                "nvr_port": "80",
                "nvr_username": "admin",
                "nvr_password": "",  # empty — don't overwrite
                "nvr_use_https": "false",
                "nvr_timeout": "15",
            },
        )
        assert response.status_code == 200

        from remander.services.app_config import get_config_value

        assert await get_config_value("nvr_host") == "10.0.0.1"

    async def test_save_nvr_empty_password_does_not_overwrite(
        self, client: AsyncClient
    ) -> None:
        """Submitting an empty password field must NOT clear the stored password."""
        from remander.services.app_config import get_config_value, set_config_value

        # Pre-store a password
        await set_config_value("nvr_password", "super-secret")

        response = await client.post(
            "/admin/settings/core/nvr",
            data={
                "nvr_host": "10.0.0.1",
                "nvr_port": "80",
                "nvr_username": "admin",
                "nvr_password": "",  # empty field — should be ignored
                "nvr_use_https": "false",
                "nvr_timeout": "15",
            },
        )
        assert response.status_code == 200
        # Password must be unchanged
        assert await get_config_value("nvr_password") == "super-secret"

    async def test_save_nvr_new_password_overwrites(self, client: AsyncClient) -> None:
        """Submitting a non-empty password must update the stored value."""
        response = await client.post(
            "/admin/settings/core/nvr",
            data={
                "nvr_host": "10.0.0.1",
                "nvr_port": "80",
                "nvr_username": "admin",
                "nvr_password": "new-password",
                "nvr_use_https": "false",
                "nvr_timeout": "15",
            },
        )
        assert response.status_code == 200

        from remander.services.app_config import get_config_value

        assert await get_config_value("nvr_password") == "new-password"

    async def test_save_location_group(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/core/location",
            data={"latitude": "51.5074", "longitude": "-0.1278"},
        )
        assert response.status_code == 200

        from remander.config import get_settings

        assert abs(get_settings().latitude - 51.5074) < 0.001

    async def test_save_returns_toast_html(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/core/location",
            data={"latitude": "0.0", "longitude": "0.0"},
        )
        assert response.status_code == 200
        # Should contain some feedback — either "Saved" or "saved"
        assert "aved" in response.text

    async def test_unknown_group_returns_404(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/core/nonexistent",
            data={},
        )
        assert response.status_code == 404


class TestSavePluginSettings:
    async def test_save_hot_water_plugin_settings(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/plugin/hot_water",
            data={
                "sonoff_ip": "192.168.50.10",
                "default_duration_minutes": "25",
                "available_durations": "10,20,30",
            },
        )
        assert response.status_code == 200

        from remander.services.app_config import get_plugin_setting

        assert get_plugin_setting("hot_water", "sonoff_ip") == "192.168.50.10"
        assert get_plugin_setting("hot_water", "default_duration_minutes") == 25
        assert get_plugin_setting("hot_water", "available_durations") == [10, 20, 30]

    async def test_save_plugin_returns_toast(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/plugin/hot_water",
            data={
                "sonoff_ip": "192.168.1.50",
                "default_duration_minutes": "20",
                "available_durations": "15,20,30",
            },
        )
        assert response.status_code == 200
        assert "aved" in response.text

    async def test_unknown_plugin_returns_404(self, client: AsyncClient) -> None:
        response = await client.post(
            "/admin/settings/plugin/no_such_plugin",
            data={},
        )
        assert response.status_code == 404
