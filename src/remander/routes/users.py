"""Admin user management routes."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from remander.auth import make_token
from remander.models.user import User
from remander.services.email import send_auth_email
from remander.services.user import create_user, get_access_history, list_users

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users")


def _templates():
    from remander.main import templates

    return templates


def _secret() -> str:
    from remander.config import get_settings

    return get_settings().session_secret_key


async def _send_invite(user: User, base_url: str) -> None:
    token = make_token(user.email, salt="invitation", secret=_secret())
    invite_url = f"{base_url}/set-password?token={token}"
    await send_auth_email(
        to=user.email,
        subject="Welcome to Remander — set your password",
        body=(
            f"Hello{' ' + user.display_name if user.display_name else ''},\n\n"
            f"An account has been created for you on Remander. "
            f"Click the link below to set your password. "
            f"This link expires in 7 days.\n\n{invite_url}\n\n"
            "If you were not expecting this, please ignore this email."
        ),
    )


@router.get("", response_class=HTMLResponse)
async def user_list(request: Request) -> HTMLResponse:
    users = await list_users()
    # Attach last-access timestamp for each user
    from remander.models.user_access_log import UserAccessLog

    last_access: dict[int, str] = {}
    for user in users:
        log = (
            await UserAccessLog.filter(user_id=user.id).order_by("-timestamp").limit(1).first()
        )
        if log:
            last_access[user.id] = log.timestamp.strftime("%Y-%m-%d %H:%M")

    return _templates().TemplateResponse(
        request,
        "admin/users.html",
        {"users": users, "last_access": last_access},
    )


@router.post("/create", response_class=Response)
async def user_create(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(""),
    is_admin: str = Form("false"),
) -> Response:
    email = email.strip().lower()
    if not email:
        return RedirectResponse(url="/admin/users", status_code=303)

    existing = await User.get_or_none(email=email)
    if existing is not None:
        users = await list_users()
        return _templates().TemplateResponse(
            request,
            "admin/users.html",
            {"users": users, "last_access": {}, "error": f"User '{email}' already exists."},
            status_code=400,
        )

    user = await create_user(
        email=email,
        display_name=display_name.strip() or None,
        is_admin=is_admin.lower() in ("true", "1", "on", "yes"),
    )
    base_url = str(request.base_url).rstrip("/")
    await _send_invite(user, base_url)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/{user_id}/toggle-active", response_class=Response)
async def user_toggle_active(request: Request, user_id: int) -> Response:
    user = await User.get_or_none(id=user_id)
    if user:
        user.is_active = not user.is_active
        await user.save(update_fields=["is_active", "updated_at"])
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/{user_id}/toggle-admin", response_class=Response)
async def user_toggle_admin(request: Request, user_id: int) -> Response:
    user = await User.get_or_none(id=user_id)
    if user:
        user.is_admin = not user.is_admin
        await user.save(update_fields=["is_admin", "updated_at"])
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/{user_id}/resend-invite", response_class=Response)
async def user_resend_invite(request: Request, user_id: int) -> Response:
    user = await User.get_or_none(id=user_id)
    if user and user.password_hash is None:
        base_url = str(request.base_url).rstrip("/")
        await _send_invite(user, base_url)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/{user_id}/history", response_class=HTMLResponse)
async def user_history(request: Request, user_id: int) -> HTMLResponse:
    user = await User.get_or_none(id=user_id)
    if user is None:
        return HTMLResponse("User not found", status_code=404)
    logs = await get_access_history(user_id, limit=200)
    return _templates().TemplateResponse(
        request,
        "admin/user_history.html",
        {"subject_user": user, "logs": logs},
    )
