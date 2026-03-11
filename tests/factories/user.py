"""Factory functions for User model instances."""

from uuid import uuid4

from remander.models.user import User
from remander.services.user import hash_password


async def create_user(**kwargs: object) -> User:
    """Create a User with sensible defaults. Override any field via kwargs."""
    defaults: dict[str, object] = {
        "email": f"user-{uuid4().hex[:6]}@example.com",
        "is_active": True,
        "is_admin": False,
    }
    defaults.update(kwargs)
    return await User.create(**defaults)


async def create_user_with_password(password: str = "testpassword1", **kwargs: object) -> User:
    """Create a User with a hashed password set."""
    user = await create_user(**kwargs)
    user.password_hash = hash_password(password)
    await user.save(update_fields=["password_hash", "updated_at"])
    return user
