"""User model — authentication and access tracking."""

from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True)
    display_name = fields.CharField(max_length=255, null=True)
    password_hash = fields.CharField(max_length=255, null=True)
    token = fields.CharField(max_length=255, null=True, unique=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations
    access_logs: fields.ReverseRelation["UserAccessLog"]

    class Meta:
        table = "user"

    def __str__(self) -> str:
        return f"User({self.id}: {self.email})"


# Import for type hints
from remander.models.user_access_log import UserAccessLog  # noqa: E402, F401
