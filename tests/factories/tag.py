"""Factory functions for Tag model instances."""

from uuid import uuid4

from remander.models.tag import Tag


async def create_tag(**kwargs: object) -> Tag:
    """Create a Tag with sensible defaults. Override any field via kwargs."""
    defaults: dict[str, object] = {
        "name": f"tag-{uuid4().hex[:6]}",
    }
    defaults.update(kwargs)
    return await Tag.create(**defaults)
