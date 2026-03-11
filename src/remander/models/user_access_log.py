"""UserAccessLog model — per-user auth event history."""

from tortoise import fields
from tortoise.models import Model


class UserAccessLog(Model):
    id = fields.IntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User",
        related_name="access_logs",
        on_delete=fields.CASCADE,
    )
    timestamp = fields.DatetimeField(auto_now_add=True)
    ip_address = fields.CharField(max_length=45, null=True)
    method = fields.CharField(max_length=20)  # password | token | password_reset | invitation
    path = fields.CharField(max_length=500, null=True)

    class Meta:
        table = "user_access_log"

    def __str__(self) -> str:
        return f"UserAccessLog({self.id}: user={self.user_id} method={self.method})"


# Import for type hints
from remander.models.user import User  # noqa: E402, F401
