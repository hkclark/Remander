"""Bitmask models — HourBitmask, ZoneMask, and DeviceBitmaskAssignment."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import DetectionType, HourBitmaskSubtype, Mode


class HourBitmask(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)
    subtype = fields.CharEnumField(HourBitmaskSubtype)
    static_value = fields.CharField(max_length=24, null=True)
    sunrise_offset_minutes = fields.IntField(null=True)
    sunset_offset_minutes = fields.IntField(null=True)
    fill_value = fields.CharField(max_length=1, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "hour_bitmask"

    def __str__(self) -> str:
        return self.name


class ZoneMask(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)
    mask_value = fields.CharField(max_length=4800)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "zone_mask"

    def __str__(self) -> str:
        return self.name


class DeviceBitmaskAssignment(Model):
    id = fields.IntField(primary_key=True)
    device: fields.ForeignKeyRelation["Device"] = fields.ForeignKeyField(
        "models.Device", related_name="bitmask_assignments", on_delete=fields.CASCADE
    )
    mode = fields.CharEnumField(Mode)
    detection_type = fields.CharEnumField(DetectionType)
    hour_bitmask: fields.ForeignKeyNullableRelation[HourBitmask] = fields.ForeignKeyField(
        "models.HourBitmask", related_name="assignments", null=True, on_delete=fields.SET_NULL
    )
    zone_mask: fields.ForeignKeyNullableRelation[ZoneMask] = fields.ForeignKeyField(
        "models.ZoneMask", related_name="assignments", null=True, on_delete=fields.SET_NULL
    )

    class Meta:
        table = "device_bitmask_assignment"
        unique_together = (("device", "mode", "detection_type"),)

    def __str__(self) -> str:
        return f"{self.device_id}:{self.mode}:{self.detection_type}"


# Import for type hint
from remander.models.device import Device  # noqa: E402, F401
