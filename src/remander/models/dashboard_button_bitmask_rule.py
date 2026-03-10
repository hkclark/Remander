"""DashboardButtonBitmaskRule model — per-tag bitmask assignments for a dashboard button."""

from tortoise import fields
from tortoise.models import Model


class DashboardButtonBitmaskRule(Model):
    id = fields.IntField(primary_key=True)
    dashboard_button: fields.ForeignKeyRelation["DashboardButton"] = fields.ForeignKeyField(
        "models.DashboardButton",
        related_name="bitmask_rules",
        on_delete=fields.CASCADE,
    )
    tag: fields.ForeignKeyRelation["Tag"] = fields.ForeignKeyField(
        "models.Tag",
        related_name="button_bitmask_rules",
        on_delete=fields.CASCADE,
    )
    hour_bitmask: fields.ForeignKeyRelation["HourBitmask"] = fields.ForeignKeyField(
        "models.HourBitmask",
        related_name="button_bitmask_rules",
        on_delete=fields.RESTRICT,
    )

    class Meta:
        table = "dashboard_button_bitmask_rule"
        unique_together = (("dashboard_button", "tag"),)

    def __str__(self) -> str:
        return f"Rule(button={self.dashboard_button_id}, tag={self.tag_id})"


# Imports for type hints
from remander.models.dashboard_button import DashboardButton  # noqa: E402, F401
from remander.models.bitmask import HourBitmask  # noqa: E402, F401
from remander.models.tag import Tag  # noqa: E402, F401
