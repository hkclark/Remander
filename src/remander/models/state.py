"""SavedDeviceState and AppState models."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import DetectionType


class SavedDeviceState(Model):
    id = fields.IntField(primary_key=True)
    command: fields.ForeignKeyRelation["Command"] = fields.ForeignKeyField(
        "models.Command", related_name="saved_states", on_delete=fields.CASCADE
    )
    device: fields.ForeignKeyRelation["Device"] = fields.ForeignKeyField(
        "models.Device", related_name="saved_states", on_delete=fields.CASCADE
    )
    detection_type = fields.CharEnumField(DetectionType)
    saved_hour_bitmask = fields.CharField(max_length=24, null=True)
    saved_zone_mask = fields.CharField(max_length=4800, null=True)
    is_consumed = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "saved_device_state"

    def __str__(self) -> str:
        return f"SavedState({self.device_id}:{self.detection_type})"


class AppState(Model):
    key = fields.CharField(max_length=100, primary_key=True)
    value = fields.CharField(max_length=500)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "app_state"

    def __str__(self) -> str:
        return f"{self.key}={self.value}"


# Import for type hints
from remander.models.command import Command  # noqa: E402, F401
from remander.models.device import Device  # noqa: E402, F401
