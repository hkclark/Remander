"""Tag and DeviceTag models for device grouping."""

from tortoise import fields
from tortoise.models import Model


class Tag(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True)
    show_on_dashboard = fields.BooleanField(default=False)
    color = fields.CharField(max_length=50, null=True)

    # Many-to-many with Device via device_tag junction table
    devices: fields.ManyToManyRelation["Device"] = fields.ManyToManyField(
        "models.Device", related_name="tags", through="device_tag"
    )

    class Meta:
        table = "tag"

    def __str__(self) -> str:
        return self.name


# Import for type hint
from remander.models.device import Device  # noqa: E402, F401
