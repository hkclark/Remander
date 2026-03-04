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

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["remander.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client for the FastAPI app.

    Note: We import the app here (not at module level) so the lifespan
    doesn't run — the setup_db fixture handles database initialization.
    """
    from remander.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
