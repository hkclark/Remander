"""Tests for auth routes — login, logout, forgot/reset password, set-password."""

import os

import pytest

os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-tests-only")

from remander.auth import make_token
from tests.factories.user import create_user, create_user_with_password

SECRET = "test-secret-key-for-tests-only"


# ── Login page ────────────────────────────────────────────────────────────────


async def test_login_page_renders(client):
    # Must have at least one user so /login doesn't redirect to /setup
    await create_user_with_password(email="logintest@example.com")
    resp = await client.get("/login")
    assert resp.status_code == 200
    assert b"Sign In" in resp.content


# ── POST /login ───────────────────────────────────────────────────────────────


async def test_login_success_redirects(client):
    await create_user_with_password("correctpass", email="login@example.com")
    resp = await client.post(
        "/login",
        data={"email": "login@example.com", "password": "correctpass", "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


async def test_login_wrong_password_returns_401(client):
    await create_user_with_password("correctpass", email="login2@example.com")
    resp = await client.post(
        "/login",
        data={"email": "login2@example.com", "password": "wrongpass", "next": "/"},
    )
    assert resp.status_code == 401
    assert b"Invalid email or password" in resp.content


async def test_login_unknown_email_returns_401(client):
    resp = await client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "whatever", "next": "/"},
    )
    assert resp.status_code == 401


async def test_login_no_password_set_returns_401(client):
    """A user created via invite but who hasn't set a password yet cannot log in."""
    await create_user(email="nopw@example.com")
    resp = await client.post(
        "/login",
        data={"email": "nopw@example.com", "password": "anything", "next": "/"},
    )
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────


async def test_logout_redirects_to_login(client):
    resp = await client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


# ── Forgot password ───────────────────────────────────────────────────────────


async def test_forgot_password_page_renders(client):
    resp = await client.get("/forgot-password")
    assert resp.status_code == 200
    assert b"Reset Password" in resp.content


async def test_forgot_password_submit_always_shows_sent(client):
    """Non-existent email still shows the confirmation message (no enumeration)."""
    resp = await client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert b"receive a password reset link" in resp.content


async def test_forgot_password_submit_registered_shows_sent(client):
    await create_user_with_password(email="reset@example.com")
    resp = await client.post("/forgot-password", data={"email": "reset@example.com"})
    assert resp.status_code == 200
    assert b"receive a password reset link" in resp.content


# ── Reset password ────────────────────────────────────────────────────────────


async def test_reset_password_page_valid_token(client):
    await create_user_with_password(email="reset2@example.com")
    token = make_token("reset2@example.com", salt="password-reset", secret=SECRET)
    resp = await client.get(f"/reset-password?token={token}")
    assert resp.status_code == 200
    assert b"Set New Password" in resp.content


async def test_reset_password_page_invalid_token_shows_expired(client):
    resp = await client.get("/reset-password?token=badtoken")
    assert resp.status_code == 200
    assert b"expired" in resp.content.lower()


async def test_reset_password_submit_success(client):
    await create_user_with_password(email="resetok@example.com")
    token = make_token("resetok@example.com", salt="password-reset", secret=SECRET)
    resp = await client.post(
        "/reset-password",
        data={"token": token, "password": "newpassword1", "password_confirm": "newpassword1"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


async def test_reset_password_mismatch_shows_error(client):
    await create_user_with_password(email="resetmm@example.com")
    token = make_token("resetmm@example.com", salt="password-reset", secret=SECRET)
    resp = await client.post(
        "/reset-password",
        data={"token": token, "password": "newpassword1", "password_confirm": "different"},
    )
    assert resp.status_code == 200
    assert b"do not match" in resp.content


# ── Set password (invitation) ─────────────────────────────────────────────────


async def test_set_password_page_valid_token(client):
    user = await create_user(email="invite@example.com")
    token = make_token(user.email, salt="invitation", secret=SECRET)
    resp = await client.get(f"/set-password?token={token}")
    assert resp.status_code == 200
    assert b"Activate Account" in resp.content


async def test_set_password_page_invalid_token_shows_expired(client):
    resp = await client.get("/set-password?token=badtoken")
    assert resp.status_code == 200
    assert b"expired" in resp.content.lower()


async def test_set_password_submit_success(client):
    user = await create_user(email="inviteok@example.com")
    token = make_token(user.email, salt="invitation", secret=SECRET)
    resp = await client.post(
        "/set-password",
        data={"token": token, "password": "mypassword1", "password_confirm": "mypassword1"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]

    # Password is now set
    from remander.models.user import User as UserModel
    updated = await UserModel.get(id=user.id)
    assert updated.password_hash is not None


async def test_set_password_already_used_shows_error(client):
    """Re-using an invite token after password is already set should fail."""
    user = await create_user_with_password(email="alreadyset@example.com")
    token = make_token(user.email, salt="invitation", secret=SECRET)
    resp = await client.post(
        "/set-password",
        data={"token": token, "password": "newpassword1", "password_confirm": "newpassword1"},
    )
    assert resp.status_code == 200
    assert b"already been used" in resp.content
