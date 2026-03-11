"""Tests for auth service and token utilities."""

import os

import pytest

os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-tests-only")

from remander.auth import make_token, verify_token
from remander.services.user import (
    create_user,
    get_access_history,
    get_user_by_email,
    get_user_by_token,
    hash_password,
    log_access,
    set_password,
    verify_password,
)
from tests.factories.user import create_user_with_password


# ── Password hashing ──────────────────────────────────────────────────────────


def test_hash_password_returns_bcrypt_hash():
    h = hash_password("secret")
    assert h.startswith("$2b$")


def test_verify_password_correct():
    h = hash_password("secret")
    assert verify_password("secret", h) is True


def test_verify_password_wrong():
    h = hash_password("secret")
    assert verify_password("wrong", h) is False


# ── Token utilities ───────────────────────────────────────────────────────────


def test_make_and_verify_token():
    token = make_token("user@example.com", salt="password-reset", secret="mysecret")
    result = verify_token(token, salt="password-reset", secret="mysecret", max_age=3600)
    assert result == "user@example.com"


def test_verify_token_wrong_salt_returns_none():
    token = make_token("user@example.com", salt="password-reset", secret="mysecret")
    result = verify_token(token, salt="invitation", secret="mysecret", max_age=3600)
    assert result is None


def test_verify_token_wrong_secret_returns_none():
    token = make_token("user@example.com", salt="password-reset", secret="mysecret")
    result = verify_token(token, salt="password-reset", secret="othersecret", max_age=3600)
    assert result is None


def test_verify_token_tampered_returns_none():
    result = verify_token("notavalidtoken", salt="password-reset", secret="mysecret", max_age=3600)
    assert result is None


# ── User CRUD ─────────────────────────────────────────────────────────────────


async def test_create_user_no_password():
    user = await create_user("alice@example.com", display_name="Alice")
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.display_name == "Alice"
    assert user.password_hash is None
    assert user.is_active is True
    assert user.is_admin is False


async def test_create_user_normalises_email():
    user = await create_user("  ALICE@Example.COM  ")
    assert user.email == "alice@example.com"


async def test_get_user_by_email_found():
    await create_user_with_password(email="bob@example.com")
    user = await get_user_by_email("bob@example.com")
    assert user is not None
    assert user.email == "bob@example.com"


async def test_get_user_by_email_case_insensitive():
    await create_user_with_password(email="bob@example.com")
    user = await get_user_by_email("BOB@EXAMPLE.COM")
    assert user is not None


async def test_get_user_by_email_inactive_returns_none():
    await create_user_with_password(email="inactive@example.com", is_active=False)
    user = await get_user_by_email("inactive@example.com")
    assert user is None


async def test_get_user_by_email_not_found():
    result = await get_user_by_email("nobody@example.com")
    assert result is None


async def test_get_user_by_token_found():
    user = await create_user_with_password(email="tok@example.com", token="mytoken123")
    found = await get_user_by_token("mytoken123")
    assert found is not None
    assert found.id == user.id


async def test_get_user_by_token_empty_returns_none():
    result = await get_user_by_token("")
    assert result is None


async def test_set_password():
    user = await create_user("newpass@example.com")
    assert user.password_hash is None
    await set_password(user, "newpassword123")
    assert user.password_hash is not None
    assert verify_password("newpassword123", user.password_hash)


# ── Access log ────────────────────────────────────────────────────────────────


async def test_log_access_creates_record():
    user = await create_user_with_password(email="log@example.com")
    log = await log_access(user, "127.0.0.1", method="password", path="/login")
    assert log.id is not None
    assert log.method == "password"
    assert log.ip_address == "127.0.0.1"


async def test_get_access_history_returns_most_recent_first():
    user = await create_user_with_password(email="hist@example.com")
    await log_access(user, "1.1.1.1", method="password", path="/login")
    await log_access(user, "2.2.2.2", method="token", path="/")
    logs = await get_access_history(user.id)
    assert len(logs) == 2
    # Most recent first
    assert logs[0].method == "token"
    assert logs[1].method == "password"
