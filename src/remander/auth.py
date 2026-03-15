"""Authentication dependencies, token utilities, and exception handler."""

import logging

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from remander.models.user import User

logger = logging.getLogger(__name__)


# ── Custom exception ──────────────────────────────────────────────────────────


class RequiresLoginException(Exception):
    """Raised when a route requires authentication but none is present.

    Handled globally by requires_login_handler() registered in main.py.
    """


async def requires_login_handler(request: Request, exc: RequiresLoginException) -> RedirectResponse:
    """Redirect unauthenticated requests to /login.

    For HTMX partial requests, use the HX-Redirect response header so HTMX
    performs a full-page navigation instead of swapping a redirect response.
    """
    prefix = request.scope.get("root_path", "")
    login_url = f"{prefix}/login?next={request.url.path}"
    if request.headers.get("HX-Request"):
        from fastapi.responses import Response

        return Response(status_code=200, headers={"HX-Redirect": login_url})
    return RedirectResponse(url=login_url, status_code=302)


# ── FastAPI dependencies ───────────────────────────────────────────────────────


async def get_current_user(request: Request) -> User:
    """Return the authenticated User from the session cookie.

    Raises RequiresLoginException if the session is missing or the user is
    inactive/deleted — the global handler redirects to /login.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise RequiresLoginException()
    user = await User.get_or_none(id=user_id, is_active=True)
    if user is None:
        request.session.clear()
        raise RequiresLoginException()
    return user


async def get_current_user_optional(request: Request) -> User | None:
    """Return the authenticated User or None — does not redirect.

    Used on public routes (dashboards) where auth is optional.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await User.get_or_none(id=user_id, is_active=True)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Extend get_current_user to require is_admin=True."""
    from fastapi import HTTPException

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Signed token utilities ────────────────────────────────────────────────────


def _serializer(secret: str, salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=salt)


def make_token(payload: str, *, salt: str, secret: str) -> str:
    """Create a signed, time-stamped token encoding `payload`."""
    return _serializer(secret, salt).dumps(payload)


def verify_token(token: str, *, salt: str, secret: str, max_age: int) -> str | None:
    """Verify and decode a signed token. Returns the payload or None if invalid/expired."""
    try:
        return _serializer(secret, salt).loads(token, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
