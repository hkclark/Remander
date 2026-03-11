"""Hot water plugin — implements the RemandPlugin protocol."""

from collections.abc import Callable
from pathlib import Path

import attrs
from fastapi import FastAPI

from remander.plugins.base import DashboardWidget, SettingField


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

    def settings_fields(self) -> list[SettingField]:
        return [
            SettingField(
                key="sonoff_ip",
                label="Sonoff Switch IP Address",
                description="IP address of the Sonoff Mini R2 that controls the hot water pump.",
                field_type="string",
                default="192.168.1.50",
            ),
            SettingField(
                key="default_duration_minutes",
                label="Default Duration (minutes)",
                description="Duration pre-selected when the hot water widget loads.",
                field_type="int",
                default=20,
            ),
            SettingField(
                key="available_durations",
                label="Available Durations",
                description="Comma-separated list of duration options shown in the widget.",
                field_type="list_int",
                default=[15, 20, 30],
            ),
        ]

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass
