"""Device model — cameras and power control devices."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import DeviceBrand, DeviceType


class Device(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)
    device_type = fields.CharEnumField(DeviceType)
    device_subtype = fields.CharField(max_length=50, null=True)
    brand = fields.CharEnumField(DeviceBrand)
    model_name = fields.CharField(max_length=255, null=True, source_field="model")
    hw_version = fields.CharField(max_length=50, null=True)
    firmware = fields.CharField(max_length=100, null=True)
    ip_address = fields.CharField(max_length=45, null=True)
    channel = fields.IntField(null=True)
    is_wireless = fields.BooleanField(default=False)
    is_poe = fields.BooleanField(default=False)
    resolution = fields.CharField(max_length=20, null=True)
    has_ptz = fields.BooleanField(default=False)
    ptz_calibration_required = fields.BooleanField(default=False)
    ptz_away_preset = fields.IntField(null=True)
    ptz_home_preset = fields.IntField(null=True)
    ptz_speed = fields.IntField(null=True)
    power_device: fields.ForeignKeyNullableRelation["Device"] = fields.ForeignKeyField(
        "models.Device", related_name="powered_cameras", null=True, on_delete=fields.SET_NULL
    )
    zone_masks_enabled = fields.BooleanField(default=False)
    zone_mask_away = fields.TextField(null=True)
    zone_mask_home = fields.TextField(null=True)
    notes = fields.TextField(null=True)
    is_enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations (declared for type hinting)
    tags: fields.ManyToManyRelation["Tag"]
    detection_types: fields.ReverseRelation["DeviceDetectionType"]
    bitmask_assignments: fields.ReverseRelation["DeviceBitmaskAssignment"]

    class Meta:
        table = "device"

    def __str__(self) -> str:
        return self.name


# Import here to avoid circular imports but enable type hints above
from remander.models.bitmask import DeviceBitmaskAssignment  # noqa: E402, F401
from remander.models.detection import DeviceDetectionType  # noqa: E402, F401
from remander.models.tag import Tag  # noqa: E402, F401
