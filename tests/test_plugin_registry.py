"""Tests for plugin registry — discovery, access, and widget collection."""

from unittest.mock import MagicMock, patch

import attrs

from remander.plugins.base import DashboardWidget, RemandPlugin
from remander.plugins.registry import PluginRegistry, get_registry, set_registry


def _make_fake_plugin(
    name: str = "test_plugin",
    version: str = "0.1.0",
    widgets: list[DashboardWidget] | None = None,
    jobs: list | None = None,
) -> RemandPlugin:
    """Build a fake plugin satisfying the RemandPlugin protocol."""
    plugin = MagicMock(spec=RemandPlugin)
    plugin.name = name
    plugin.version = version
    plugin.dashboard_widgets.return_value = widgets or []
    plugin.register_jobs.return_value = jobs or []
    plugin.register_templates.return_value = None
    return plugin


class TestPluginRegistry:
    def test_empty_registry(self) -> None:
        registry = PluginRegistry()
        assert registry.plugins == []

    def test_is_attrs_class(self) -> None:
        assert attrs.has(PluginRegistry)

    def test_register_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = _make_fake_plugin()
        registry.register(plugin)
        assert len(registry.plugins) == 1
        assert registry.plugins[0] is plugin

    def test_get_by_name(self) -> None:
        registry = PluginRegistry()
        plugin = _make_fake_plugin(name="hot_water")
        registry.register(plugin)
        assert registry.get("hot_water") is plugin

    def test_get_missing_returns_none(self) -> None:
        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_all_dashboard_widgets_filters_by_target(self) -> None:
        registry = PluginRegistry()
        w1 = DashboardWidget(
            plugin_name="p1", template_name="t1.html", target="dashboard", sort_order=10
        )
        w2 = DashboardWidget(
            plugin_name="p1", template_name="t2.html", target="guest_dashboard", sort_order=20
        )
        plugin = _make_fake_plugin(widgets=[w1, w2])
        registry.register(plugin)

        dash_widgets = registry.all_dashboard_widgets("dashboard")
        assert dash_widgets == [w1]

        guest_widgets = registry.all_dashboard_widgets("guest_dashboard")
        assert guest_widgets == [w2]

    def test_all_dashboard_widgets_sorted_by_sort_order(self) -> None:
        registry = PluginRegistry()
        w_high = DashboardWidget(
            plugin_name="p1", template_name="t1.html", target="dashboard", sort_order=200
        )
        w_low = DashboardWidget(
            plugin_name="p2", template_name="t2.html", target="dashboard", sort_order=50
        )
        p1 = _make_fake_plugin(name="p1", widgets=[w_high])
        p2 = _make_fake_plugin(name="p2", widgets=[w_low])
        registry.register(p1)
        registry.register(p2)

        widgets = registry.all_dashboard_widgets("dashboard")
        assert widgets == [w_low, w_high]

    def test_all_job_handlers(self) -> None:
        registry = PluginRegistry()

        async def fake_job(ctx, **kwargs):
            pass

        plugin = _make_fake_plugin(jobs=[("my_job", fake_job)])
        registry.register(plugin)

        handlers = registry.all_job_handlers()
        assert len(handlers) == 1
        assert handlers[0] == ("my_job", fake_job)

    @patch("remander.plugins.registry.entry_points")
    def test_discover_loads_entry_points(self, mock_ep) -> None:
        """discover() should call entry point factories and register results."""
        plugin = _make_fake_plugin(name="discovered")
        factory = MagicMock(return_value=plugin)

        ep = MagicMock()
        ep.name = "discovered"
        ep.load.return_value = factory
        mock_ep.return_value = [ep]

        registry = PluginRegistry()
        registry.discover()

        assert len(registry.plugins) == 1
        assert registry.get("discovered") is plugin

    @patch("remander.plugins.registry.entry_points")
    def test_discover_skips_bad_entry_point(self, mock_ep) -> None:
        """discover() should log and skip entry points that raise on load."""
        ep = MagicMock()
        ep.name = "broken"
        ep.load.side_effect = ImportError("bad module")
        mock_ep.return_value = [ep]

        registry = PluginRegistry()
        registry.discover()  # should not raise
        assert registry.plugins == []


class TestModuleLevelRegistry:
    def test_get_set_registry(self) -> None:
        registry = PluginRegistry()
        set_registry(registry)
        assert get_registry() is registry

    def test_get_registry_returns_empty_when_unset(self) -> None:
        """get_registry should return a default empty registry if none set."""
        set_registry(None)  # type: ignore[arg-type]
        reg = get_registry()
        assert isinstance(reg, PluginRegistry)
        assert reg.plugins == []
