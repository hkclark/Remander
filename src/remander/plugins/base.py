"""Plugin protocol and widget descriptor for the Remander plugin system."""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

import attrs
from fastapi import FastAPI


@attrs.define
class DashboardWidget:
    """Describes a widget that a plugin contributes to a dashboard."""

    plugin_name: str
    template_name: str  # e.g. "hot_water/_widget.html"
    target: str  # "dashboard" or "guest_dashboard"
    sort_order: int = 100


@attrs.define
class SettingField:
    """Declares a single configurable field that a plugin exposes to the admin UI."""

    key: str  # field name, e.g. "sonoff_ip"
    label: str  # human-readable label, e.g. "Sonoff Switch IP Address"
    description: str = ""
    field_type: str = "string"  # "string" | "int" | "bool" | "float" | "list_int"
    default: Any = None
    secret: bool = False  # renders as password input
    restart_required: bool = False  # shows a "restart required" badge


@runtime_checkable
class RemandPlugin(Protocol):
    """Contract every Remander plugin must satisfy."""

    name: str
    version: str

    def register_routes(self, app: FastAPI) -> None: ...

    def register_templates(self) -> str | None: ...

    def register_jobs(self) -> list[tuple[str, Callable]]: ...

    def dashboard_widgets(self) -> list[DashboardWidget]: ...

    def settings_fields(self) -> list[SettingField]: ...

    async def on_startup(self) -> None: ...

    async def on_shutdown(self) -> None: ...
