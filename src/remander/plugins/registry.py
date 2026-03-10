"""Plugin registry — discovers and manages Remander plugins."""

import logging
from collections.abc import Callable
from importlib.metadata import entry_points

import attrs

from remander.plugins.base import DashboardWidget, RemandPlugin

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "remander.plugins"


@attrs.define
class PluginRegistry:
    """Central registry that discovers, stores, and queries plugins."""

    _plugins: list[RemandPlugin] = attrs.field(factory=list)

    @property
    def plugins(self) -> list[RemandPlugin]:
        return list(self._plugins)

    def register(self, plugin: RemandPlugin) -> None:
        """Register a plugin instance."""
        self._plugins.append(plugin)
        logger.info("Registered plugin '%s' (v%s)", plugin.name, plugin.version)

    def get(self, name: str) -> RemandPlugin | None:
        """Look up a plugin by name."""
        for plugin in self._plugins:
            if plugin.name == name:
                return plugin
        return None

    def all_dashboard_widgets(self, target: str) -> list[DashboardWidget]:
        """Collect all dashboard widgets for a given target, sorted by sort_order."""
        widgets: list[DashboardWidget] = []
        for plugin in self._plugins:
            for widget in plugin.dashboard_widgets():
                if widget.target == target:
                    widgets.append(widget)
        return sorted(widgets, key=lambda w: w.sort_order)

    def all_job_handlers(self) -> list[tuple[str, Callable]]:
        """Collect all SAQ job handlers from all plugins."""
        handlers: list[tuple[str, Callable]] = []
        for plugin in self._plugins:
            handlers.extend(plugin.register_jobs())
        return handlers

    def discover(self) -> None:
        """Discover plugins via Python entry points."""
        eps = entry_points(group=ENTRY_POINT_GROUP)
        for ep in eps:
            try:
                factory = ep.load()
                plugin = factory()
                self.register(plugin)
                logger.info(
                    "Loaded plugin '%s' (v%s) from entry point '%s'",
                    plugin.name,
                    plugin.version,
                    ep.name,
                )
            except Exception:
                logger.exception("Failed to load plugin from entry point '%s'", ep.name)


# Module-level singleton (same pattern as worker.py queue)
_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Return the module-level registry, creating a default if unset."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def set_registry(registry: PluginRegistry | None) -> None:
    """Set the module-level registry (called during lifespan)."""
    global _registry
    _registry = registry
