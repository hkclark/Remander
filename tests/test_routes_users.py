"""Tests for admin user management routes."""

import pytest

from tests.factories.user import create_user, create_user_with_password


async def test_user_list_renders(logged_in_client):
    await create_user_with_password(email="listed@example.com")
    resp = await logged_in_client.get("/admin/users")
    assert resp.status_code == 200
    assert b"listed@example.com" in resp.content


async def test_user_list_shows_pending_invite_badge(logged_in_client):
    await create_user(email="pending@example.com")
    resp = await logged_in_client.get("/admin/users")
    assert resp.status_code == 200
    assert b"Pending invite" in resp.content


async def test_create_user_redirects(logged_in_client):
    resp = await logged_in_client.post(
        "/admin/users/create",
        data={"email": "newuser@example.com", "display_name": "New User", "is_admin": "false"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from remander.models.user import User
    user = await User.get_or_none(email="newuser@example.com")
    assert user is not None
    assert user.display_name == "New User"
    assert user.password_hash is None  # invite not yet accepted


async def test_create_duplicate_user_returns_400(logged_in_client):
    await create_user(email="dup@example.com")
    resp = await logged_in_client.post(
        "/admin/users/create",
        data={"email": "dup@example.com", "display_name": ""},
    )
    assert resp.status_code == 400
    assert b"already exists" in resp.content


async def test_toggle_active_disables_user(logged_in_client):
    user = await create_user_with_password(email="toggle@example.com")
    assert user.is_active is True

    resp = await logged_in_client.post(
        f"/admin/users/{user.id}/toggle-active", follow_redirects=False
    )
    assert resp.status_code == 303

    from remander.models.user import User
    updated = await User.get(id=user.id)
    assert updated.is_active is False


async def test_toggle_active_re_enables_user(logged_in_client):
    user = await create_user_with_password(email="reenable@example.com", is_active=False)

    await logged_in_client.post(f"/admin/users/{user.id}/toggle-active", follow_redirects=False)

    from remander.models.user import User
    updated = await User.get(id=user.id)
    assert updated.is_active is True


async def test_toggle_admin_grants_flag(logged_in_client):
    user = await create_user_with_password(email="admin_toggle@example.com", is_admin=False)

    await logged_in_client.post(f"/admin/users/{user.id}/toggle-admin", follow_redirects=False)

    from remander.models.user import User
    updated = await User.get(id=user.id)
    assert updated.is_admin is True


async def test_user_history_renders(logged_in_client):
    user = await create_user_with_password(email="history@example.com")

    from remander.services.user import log_access
    await log_access(user, "127.0.0.1", method="password", path="/login")

    resp = await logged_in_client.get(f"/admin/users/{user.id}/history")
    assert resp.status_code == 200
    assert b"history@example.com" in resp.content
    assert b"password" in resp.content


async def test_user_history_unknown_user_404(logged_in_client):
    resp = await logged_in_client.get("/admin/users/99999/history")
    assert resp.status_code == 404
