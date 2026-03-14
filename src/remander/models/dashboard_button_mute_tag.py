"""DashboardButtonMuteTag model — tags whose cameras are silenced during ingress/egress."""

from tortoise import fields
from tortoise.models import Model


class DashboardButtonMuteTag(Model):
    id = fields.IntField(primary_key=True)
    dashboard_button: fields.ForeignKeyRelation["DashboardButton"] = fields.ForeignKeyField(
        "models.DashboardButton",
        related_name="mute_tags",
        on_delete=fields.CASCADE,
    )
    tag: fields.ForeignKeyRelation["Tag"] = fields.ForeignKeyField(
        "models.Tag",
        related_name="button_mute_tags",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "dashboard_button_mute_tag"
        unique_together = (("dashboard_button", "tag"),)

    def __str__(self) -> str:
        return f"MuteTag(button={self.dashboard_button_id}, tag={self.tag_id})"


# Imports for type hints
from remander.models.dashboard_button import DashboardButton  # noqa: E402, F401
from remander.models.tag import Tag  # noqa: E402, F401
