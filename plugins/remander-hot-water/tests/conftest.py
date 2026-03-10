"""Test fixtures for the hot water plugin."""

import os
from collections.abc import AsyncIterator

import pytest
from tortoise import Tortoise


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncIterator[None]:
    """Initialize an in-memory SQLite database for each test."""
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
