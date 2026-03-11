"""Shared test fixtures for Remander."""

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncIterator[None]:
    """Initialize an in-memory SQLite database for each test."""
    # Set required env vars for Settings (used if main.py imports config)
    os.environ.setdefault("NVR_HOST", "192.168.1.100")
    os.environ.setdefault("NVR_USERNAME", "admin")
    os.environ.setdefault("NVR_PASSWORD", "testpass")
    os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
    os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-tests-only")

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["remander.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client for the FastAPI app (unauthenticated).

    Note: We import the app here (not at module level) so the lifespan
    doesn't run — the setup_db fixture handles database initialization.
    """
    from remander.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def logged_in_client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client with a fake authenticated user injected.

    Uses FastAPI's dependency_overrides to bypass the session/DB lookup.
    The fake user is an admin so it works for both protected and admin routes.
    """
    from remander.auth import get_current_user, require_admin
    from remander.main import app
    from remander.models.user import User

    fake_user = User(
        id=1,
        email="test@example.com",
        display_name="Test User",
        is_active=True,
        is_admin=True,
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_admin] = lambda: fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
