"""Plugin protocol and widget descriptor for the Remander plugin system."""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

import attrs
from fastapi import FastAPI


@attrs.define
class DashboardWidget:
    """Describes a widget that a plugin contributes to a dashboard."""

    plugin_name: str
    template_name: str  # e.g. "hot_water/_widget.html"
    target: str  # "dashboard" or "guest_dashboard"
    sort_order: int = 100


@runtime_checkable
class RemandPlugin(Protocol):
    """Contract every Remander plugin must satisfy."""

    name: str
    version: str

    def register_routes(self, app: FastAPI) -> None: ...

    def register_templates(self) -> str | None: ...

    def register_jobs(self) -> list[tuple[str, Callable]]: ...

    def dashboard_widgets(self) -> list[DashboardWidget]: ...

    async def on_startup(self) -> None: ...

    async def on_shutdown(self) -> None: ...
