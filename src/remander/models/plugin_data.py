"""Plugin data model — generic KV store for plugin state."""

from tortoise import fields
from tortoise.models import Model


class PluginData(Model):
    """Key-value store for plugin data, avoiding per-plugin migrations."""

    id = fields.IntField(primary_key=True)
    plugin_name = fields.CharField(max_length=100, db_index=True)
    key = fields.CharField(max_length=255)
    value = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "plugin_data"
        unique_together = (("plugin_name", "key"),)
