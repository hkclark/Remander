"""Tests for the first-run /setup bootstrap route."""

import pytest
from tests.factories.user import create_user_with_password


async def test_setup_page_renders_when_no_users(client):
    resp = await client.get("/setup")
    assert resp.status_code == 200
    assert b"Create Admin Account" in resp.content


async def test_setup_page_returns_404_when_users_exist(client):
    await create_user_with_password(email="existing@example.com")
    resp = await client.get("/setup")
    assert resp.status_code == 404


async def test_setup_creates_admin_and_redirects(client):
    resp = await client.post(
        "/setup",
        data={
            "email": "admin@example.com",
            "display_name": "Admin",
            "password": "adminpass1",
            "password_confirm": "adminpass1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]

    from remander.models.user import User

    user = await User.get_or_none(email="admin@example.com")
    assert user is not None
    assert user.is_admin is True
    assert user.password_hash is not None


async def test_setup_post_returns_404_when_users_exist(client):
    await create_user_with_password(email="existing@example.com")
    resp = await client.post(
        "/setup",
        data={
            "email": "second@example.com",
            "password": "adminpass1",
            "password_confirm": "adminpass1",
        },
    )
    assert resp.status_code == 404


async def test_setup_password_mismatch_shows_error(client):
    resp = await client.post(
        "/setup",
        data={
            "email": "admin@example.com",
            "password": "adminpass1",
            "password_confirm": "different",
        },
    )
    assert resp.status_code == 200
    assert b"do not match" in resp.content


async def test_setup_password_too_short_shows_error(client):
    resp = await client.post(
        "/setup",
        data={
            "email": "admin@example.com",
            "password": "short",
            "password_confirm": "short",
        },
    )
    assert resp.status_code == 200
    assert b"8 characters" in resp.content


async def test_login_redirects_to_setup_when_no_users(client):
    resp = await client.get("/login", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/setup"


async def test_login_does_not_redirect_to_setup_when_users_exist(client):
    await create_user_with_password(email="existing@example.com")
    resp = await client.get("/login", follow_redirects=False)
    assert resp.status_code == 200  # renders login form, no redirect
