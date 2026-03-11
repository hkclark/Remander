"""User service — CRUD, password hashing, access logging."""

import bcrypt

from remander.models.user import User
from remander.models.user_access_log import UserAccessLog


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def create_user(
    email: str,
    *,
    display_name: str | None = None,
    is_admin: bool = False,
) -> User:
    """Create a new user with no password set (pending invitation)."""
    return await User.create(
        email=email.lower().strip(),
        display_name=display_name,
        is_admin=is_admin,
    )


async def get_user_by_email(email: str) -> User | None:
    """Look up an active user by email (case-insensitive)."""
    return await User.get_or_none(email=email.lower().strip(), is_active=True)


async def get_user_by_token(token: str) -> User | None:
    """Look up an active user by personal token."""
    if not token:
        return None
    return await User.get_or_none(token=token, is_active=True)


async def set_password(user: User, plain: str) -> None:
    """Hash and save a new password for the user."""
    user.password_hash = hash_password(plain)
    await user.save(update_fields=["password_hash", "updated_at"])


async def list_users() -> list[User]:
    """Return all users ordered by email."""
    return await User.all().order_by("email")


async def log_access(
    user: User,
    ip_address: str | None,
    *,
    method: str,
    path: str | None = None,
) -> UserAccessLog:
    """Create a UserAccessLog entry."""
    return await UserAccessLog.create(
        user=user,
        ip_address=ip_address,
        method=method,
        path=path,
    )


async def get_access_history(user_id: int, *, limit: int = 100) -> list[UserAccessLog]:
    """Return access log entries for a user, most recent first."""
    return (
        await UserAccessLog.filter(user_id=user_id)
        .order_by("-timestamp")
        .limit(limit)
    )
