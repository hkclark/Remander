"""Factory functions for Command model instances."""

from remander.models.command import Command
from remander.models.enums import CommandStatus, CommandType


async def create_command(**kwargs: object) -> Command:
    """Create a Command with sensible defaults. Override any field via kwargs."""
    defaults: dict[str, object] = {
        "command_type": CommandType.SET_AWAY_NOW,
        "status": CommandStatus.PENDING,
    }
    defaults.update(kwargs)
    return await Command.create(**defaults)
