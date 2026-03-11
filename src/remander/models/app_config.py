"""AppConfig model — key-value store for application and plugin settings."""

from tortoise import fields
from tortoise.models import Model


class AppConfig(Model):
    """Stores application and plugin settings, overlaying .env defaults.

    Key namespacing:
    - Core settings: plain field name (e.g. "nvr_host", "smtp_port")
    - Plugin settings: "plugin.{name}.{field}" (e.g. "plugin.hot_water.sonoff_ip")
    """

    key = fields.CharField(max_length=200, primary_key=True)
    value = fields.JSONField()
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "app_config"
