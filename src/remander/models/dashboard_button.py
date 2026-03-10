"""DashboardButton model — configurable dashboard action buttons."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import ButtonColor, ButtonOperationType


class DashboardButton(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    color = fields.CharEnumField(ButtonColor, default=ButtonColor.BLUE)
    delay_seconds = fields.IntField(default=0)
    operation_type = fields.CharEnumField(ButtonOperationType)
    sort_order = fields.IntField(default=0)
    is_enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "dashboard_button"

    def __str__(self) -> str:
        return self.name

    # bitmask_rules reverse relation is defined on DashboardButtonBitmaskRule

    @property
    def tailwind_classes(self) -> str:
        """Return Tailwind bg + hover classes for this button's color."""
        mapping = {
            ButtonColor.BLUE: "bg-blue-600 hover:bg-blue-700",
            ButtonColor.INDIGO: "bg-indigo-600 hover:bg-indigo-700",
            ButtonColor.PURPLE: "bg-purple-600 hover:bg-purple-700",
            ButtonColor.PINK: "bg-pink-600 hover:bg-pink-700",
            ButtonColor.ROSE: "bg-rose-600 hover:bg-rose-700",
            ButtonColor.RED: "bg-red-600 hover:bg-red-700",
            ButtonColor.ORANGE: "bg-orange-500 hover:bg-orange-600",
            ButtonColor.AMBER: "bg-amber-500 hover:bg-amber-600",
            ButtonColor.YELLOW: "bg-yellow-400 hover:bg-yellow-500 text-gray-900",
            ButtonColor.LIME: "bg-lime-500 hover:bg-lime-600",
            ButtonColor.GREEN: "bg-green-600 hover:bg-green-700",
            ButtonColor.TEAL: "bg-teal-600 hover:bg-teal-700",
            ButtonColor.CYAN: "bg-cyan-500 hover:bg-cyan-600",
            ButtonColor.SKY: "bg-sky-500 hover:bg-sky-600",
            ButtonColor.GRAY: "bg-gray-500 hover:bg-gray-600",
        }
        return mapping.get(self.color, "bg-blue-600 hover:bg-blue-700")

