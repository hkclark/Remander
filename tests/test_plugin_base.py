"""Tests for plugin protocol and widget descriptor."""

import attrs

from remander.plugins.base import DashboardWidget, RemandPlugin


class TestDashboardWidget:
    def test_create_widget_with_defaults(self) -> None:
        widget = DashboardWidget(
            plugin_name="test_plugin",
            template_name="test/_widget.html",
            target="dashboard",
        )
        assert widget.plugin_name == "test_plugin"
        assert widget.template_name == "test/_widget.html"
        assert widget.target == "dashboard"
        assert widget.sort_order == 100

    def test_create_widget_custom_sort_order(self) -> None:
        widget = DashboardWidget(
            plugin_name="test_plugin",
            template_name="test/_widget.html",
            target="guest_dashboard",
            sort_order=50,
        )
        assert widget.sort_order == 50
        assert widget.target == "guest_dashboard"

    def test_widget_is_attrs_class(self) -> None:
        assert attrs.has(DashboardWidget)


class TestRemandPlugin:
    def test_protocol_is_runtime_checkable(self) -> None:
        """RemandPlugin should be a runtime-checkable Protocol."""

        class FakePlugin:
            name = "fake"
            version = "0.1.0"

            def register_routes(self, app):
                pass

            def register_templates(self):
                return None

            def register_jobs(self):
                return []

            def dashboard_widgets(self):
                return []

            async def on_startup(self):
                pass

            async def on_shutdown(self):
                pass

        assert isinstance(FakePlugin(), RemandPlugin)

    def test_non_conforming_object_fails_check(self) -> None:
        """An object missing required methods should not match the protocol."""

        class NotAPlugin:
            name = "nope"

        assert not isinstance(NotAPlugin(), RemandPlugin)
