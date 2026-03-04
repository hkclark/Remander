"""ActivityLog model — per-step, per-device execution records."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import ActivityStatus


class ActivityLog(Model):
    id = fields.IntField(primary_key=True)
    command: fields.ForeignKeyRelation["Command"] = fields.ForeignKeyField(
        "models.Command", related_name="activity_logs", on_delete=fields.CASCADE
    )
    device: fields.ForeignKeyNullableRelation["Device"] = fields.ForeignKeyField(
        "models.Device", related_name="activity_logs", null=True, on_delete=fields.SET_NULL
    )
    step_name = fields.CharField(max_length=100)
    status = fields.CharEnumField(ActivityStatus)
    detail = fields.TextField(null=True)
    duration_ms = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "activity_log"

    def __str__(self) -> str:
        return f"ActivityLog({self.step_name}: {self.status})"


# Import for type hints
from remander.models.command import Command  # noqa: E402, F401
from remander.models.device import Device  # noqa: E402, F401
