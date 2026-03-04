"""Command model — tracks user-initiated operations."""

from tortoise import fields
from tortoise.models import Model

from remander.models.enums import CommandStatus, CommandType


class Command(Model):
    id = fields.IntField(primary_key=True)
    command_type = fields.CharEnumField(CommandType)
    status = fields.CharEnumField(CommandStatus, default=CommandStatus.PENDING)
    delay_minutes = fields.IntField(null=True)
    pause_minutes = fields.IntField(null=True)
    tag_filter = fields.CharField(max_length=500, null=True)
    initiated_by_ip = fields.CharField(max_length=45, null=True)
    initiated_by_user = fields.CharField(max_length=255, null=True)
    saq_job_id = fields.CharField(max_length=255, null=True)
    error_summary = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    queued_at = fields.DatetimeField(null=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    # Reverse relations
    activity_logs: fields.ReverseRelation["ActivityLog"]
    saved_states: fields.ReverseRelation["SavedDeviceState"]

    class Meta:
        table = "command"

    def __str__(self) -> str:
        return f"Command({self.id}: {self.command_type} [{self.status}])"


# Import for type hints
from remander.models.activity import ActivityLog  # noqa: E402, F401
from remander.models.state import SavedDeviceState  # noqa: E402, F401
