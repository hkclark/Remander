"""DashboardButton model — configurable dashboard action buttons."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import ButtonOperationType


class DashboardButton(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    color = fields.CharField(max_length=7, default="#3B82F6")
    delay_seconds = fields.IntField(default=0)
    operation_type = fields.CharEnumField(ButtonOperationType)
    sort_order = fields.IntField(default=0)
    is_enabled = fields.BooleanField(default=True)
    show_on_main = fields.BooleanField(default=True)
    show_on_guest = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "dashboard_button"

    def __str__(self) -> str:
        return self.name

    # bitmask_rules reverse relation is defined on DashboardButtonBitmaskRule

    @property
    def button_style(self) -> str:
        """Return an inline CSS style string for this button's background and text color."""
        from remander.app_colors import DEFAULT_BUTTON_COLOR, hex_color_style

        return hex_color_style(self.color, default=DEFAULT_BUTTON_COLOR)
