"""Tortoise ORM configuration."""

import os


def get_tortoise_config(database_url: str | None = None) -> dict:
    """Build the Tortoise ORM config dict.

    Args:
        database_url: Override the database URL (useful for testing).
    """
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL", "sqlite:///app/data/remander.db")
    return {
        "connections": {"default": database_url},
        "apps": {
            "models": {
                "models": ["remander.models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }


# Aerich requires a module-level TORTOISE_ORM dict.
# Uses DATABASE_URL env var or default; avoids requiring all settings at import time.
TORTOISE_ORM = get_tortoise_config()
