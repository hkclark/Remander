"""Auth route handlers — login, logout, password reset, invitation."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from remander.auth import get_current_user_optional, make_token, verify_token
from remander.services.email import send_auth_email
from remander.services.user import (
    create_user,
    get_user_by_email,
    log_access,
    set_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _templates():
    from remander.main import templates

    return templates


def _secret() -> str:
    from remander.config import get_settings

    return get_settings().session_secret_key


def _reset_expiry() -> int:
    from remander.config import get_settings

    return get_settings().password_reset_expiry_seconds


def _invite_expiry() -> int:
    from remander.config import get_settings

    return get_settings().invitation_expiry_seconds


# ── Login / Logout ────────────────────────────────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/maindboard", message: str = "") -> HTMLResponse:
    prefix = request.scope.get("root_path", "")
    # Fresh install with no users — redirect to setup
    if await _no_users_exist():
        return RedirectResponse(url=f"{prefix}/setup", status_code=302)
    user = await get_current_user_optional(request)
    if user is not None:
        return RedirectResponse(url=f"{prefix}{next}", status_code=302)
    return _templates().TemplateResponse(
        request, "auth/login.html", {"next": next, "message": message, "error": ""}
    )


@router.post("/login", response_class=Response)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/maindboard"),
) -> Response:
    templates = _templates()
    ctx = {"next": next, "message": "", "error": ""}

    user = await get_user_by_email(email)
    if user is None or user.password_hash is None:
        ctx["error"] = "Invalid email or password."
        return templates.TemplateResponse(request, "auth/login.html", ctx, status_code=401)

    if not verify_password(password, user.password_hash):
        ctx["error"] = "Invalid email or password."
        return templates.TemplateResponse(request, "auth/login.html", ctx, status_code=401)

    request.session["user_id"] = user.id
    ip = request.client.host if request.client else None
    await log_access(user, ip, method="password", path=next)
    prefix = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{prefix}{next or '/maindboard'}", status_code=303)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    prefix = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{prefix}/login", status_code=302)


# ── Forgot / Reset password ───────────────────────────────────────────────────


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request) -> HTMLResponse:
    return _templates().TemplateResponse(request, "auth/forgot_password.html", {"sent": False})


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(request: Request, email: str = Form(...)) -> HTMLResponse:
    user = await get_user_by_email(email)
    if user is not None:
        token = make_token(user.email, salt="password-reset", secret=_secret())
        base_url = str(request.base_url).rstrip("/") + request.scope.get("root_path", "")
        reset_url = f"{base_url}/reset-password?token={token}"
        await send_auth_email(
            to=user.email,
            subject="Remander — Reset your password",
            body=(
                f"Hello{' ' + user.display_name if user.display_name else ''},\n\n"
                f"Click the link below to reset your password. "
                f"This link expires in 1 hour.\n\n{reset_url}\n\n"
                "If you did not request this, you can ignore this email."
            ),
        )
    # Always show the same message to prevent email enumeration
    return _templates().TemplateResponse(request, "auth/forgot_password.html", {"sent": True})


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = "") -> HTMLResponse:
    email = verify_token(token, salt="password-reset", secret=_secret(), max_age=_reset_expiry())
    if not email:
        return _templates().TemplateResponse(
            request, "auth/reset_password.html", {"token": "", "expired": True}
        )
    return _templates().TemplateResponse(
        request, "auth/reset_password.html", {"token": token, "expired": False, "error": ""}
    )


@router.post("/reset-password", response_class=Response)
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
) -> Response:
    templates = _templates()
    ctx = {"token": token, "expired": False, "error": ""}

    email = verify_token(token, salt="password-reset", secret=_secret(), max_age=_reset_expiry())
    if not email:
        return templates.TemplateResponse(
            request, "auth/reset_password.html", {"token": "", "expired": True}
        )

    if password != password_confirm:
        ctx["error"] = "Passwords do not match."
        return templates.TemplateResponse(request, "auth/reset_password.html", ctx)

    if len(password) < 8:
        ctx["error"] = "Password must be at least 8 characters."
        return templates.TemplateResponse(request, "auth/reset_password.html", ctx)

    user = await get_user_by_email(email)
    if user is None:
        return templates.TemplateResponse(
            request, "auth/reset_password.html", {"token": "", "expired": True}
        )

    await set_password(user, password)
    ip = request.client.host if request.client else None
    await log_access(user, ip, method="password_reset", path="/reset-password")
    prefix = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{prefix}/login?message=Password+updated+successfully", status_code=303)


# ── Invitation / Set initial password ────────────────────────────────────────


@router.get("/set-password", response_class=HTMLResponse)
async def set_password_page(request: Request, token: str = "") -> HTMLResponse:
    email = verify_token(token, salt="invitation", secret=_secret(), max_age=_invite_expiry())
    if not email:
        return _templates().TemplateResponse(
            request, "auth/set_password.html", {"token": "", "expired": True}
        )
    return _templates().TemplateResponse(
        request, "auth/set_password.html", {"token": token, "expired": False, "error": ""}
    )


@router.post("/set-password", response_class=Response)
async def set_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
) -> Response:
    templates = _templates()
    ctx = {"token": token, "expired": False, "error": ""}

    email = verify_token(token, salt="invitation", secret=_secret(), max_age=_invite_expiry())
    if not email:
        return templates.TemplateResponse(
            request, "auth/set_password.html", {"token": "", "expired": True}
        )

    if password != password_confirm:
        ctx["error"] = "Passwords do not match."
        return templates.TemplateResponse(request, "auth/set_password.html", ctx)

    if len(password) < 8:
        ctx["error"] = "Password must be at least 8 characters."
        return templates.TemplateResponse(request, "auth/set_password.html", ctx)

    from remander.models.user import User

    user = await User.get_or_none(email=email)
    if user is None or not user.is_active:
        return templates.TemplateResponse(
            request, "auth/set_password.html", {"token": "", "expired": True}
        )

    if user.password_hash is not None:
        ctx["error"] = "This invitation link has already been used. Please log in."
        return templates.TemplateResponse(request, "auth/set_password.html", ctx)

    await set_password(user, password)
    ip = request.client.host if request.client else None
    await log_access(user, ip, method="invitation", path="/set-password")
    prefix = request.scope.get("root_path", "")
    return RedirectResponse(
        url=f"{prefix}/login?message=Account+activated.+You+can+now+log+in.", status_code=303
    )


# ── First-run setup ───────────────────────────────────────────────────────────


async def _no_users_exist() -> bool:
    from remander.models.user import User

    return await User.all().count() == 0


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request) -> HTMLResponse:
    """First-run admin account creation. Returns 404 once any user exists."""
    if not await _no_users_exist():
        from fastapi import HTTPException

        raise HTTPException(status_code=404)
    return _templates().TemplateResponse(request, "auth/setup.html", {"error": ""})


@router.post("/setup", response_class=Response)
async def setup_submit(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
) -> Response:
    """Create the first admin user. Returns 404 once any user exists."""
    if not await _no_users_exist():
        from fastapi import HTTPException

        raise HTTPException(status_code=404)

    templates = _templates()
    ctx: dict = {"error": ""}

    if password != password_confirm:
        ctx["error"] = "Passwords do not match."
        return templates.TemplateResponse(request, "auth/setup.html", ctx)

    if len(password) < 8:
        ctx["error"] = "Password must be at least 8 characters."
        return templates.TemplateResponse(request, "auth/setup.html", ctx)

    user = await create_user(
        email=email,
        display_name=display_name.strip() or None,
        is_admin=True,
    )
    await set_password(user, password)
    ip = request.client.host if request.client else None
    await log_access(user, ip, method="invitation", path="/setup")
    prefix = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{prefix}/login?message=Admin+account+created.+Please+sign+in.", status_code=303)
