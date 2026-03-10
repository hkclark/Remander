"""Hot water plugin — implements the RemandPlugin protocol."""

from collections.abc import Callable
from pathlib import Path

import attrs
from fastapi import FastAPI

from remander.plugins.base import DashboardWidget


@attrs.define
class HotWaterPlugin:
    """Plugin that controls a hot water recirculation pump via a Sonoff switch."""

    name: str = "hot_water"
    version: str = "0.1.0"

    def register_routes(self, app: FastAPI) -> None:
        from remander_hot_water.routes import router

        app.include_router(router)

    def register_templates(self) -> str | None:
        return str(Path(__file__).resolve().parent / "templates")

    def register_jobs(self) -> list[tuple[str, Callable]]:
        from remander_hot_water.jobs import turn_off_hot_water

        return [("turn_off_hot_water", turn_off_hot_water)]

    def dashboard_widgets(self) -> list[DashboardWidget]:
        return [
            DashboardWidget(
                plugin_name=self.name,
                template_name="hot_water/_dashboard_widget.html",
                target="dashboard",
                sort_order=50,
            ),
            DashboardWidget(
                plugin_name=self.name,
                template_name="hot_water/_guest_widget.html",
                target="guest_dashboard",
                sort_order=50,
            ),
        ]

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass
