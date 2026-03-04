"""DeviceDetectionType model — tracks which detection types a device supports."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import DetectionType


class DeviceDetectionType(Model):
    id = fields.IntField(primary_key=True)
    device: fields.ForeignKeyRelation["Device"] = fields.ForeignKeyField(
        "models.Device", related_name="detection_types", on_delete=fields.CASCADE
    )
    detection_type = fields.CharEnumField(DetectionType)
    is_enabled = fields.BooleanField(default=True)

    class Meta:
        table = "device_detection_type"
        unique_together = (("device", "detection_type"),)

    def __str__(self) -> str:
        return f"{self.device_id}:{self.detection_type}"


# Import for type hint
from remander.models.device import Device  # noqa: E402, F401
