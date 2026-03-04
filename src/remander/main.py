"""FastAPI application entrypoint."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from tortoise import Tortoise

from remander.config import get_settings
from remander.db import get_tortoise_config
from remander.logging import setup_logging
from remander.worker import create_queue, create_worker, set_queue

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — initialize and tear down resources."""
    settings = get_settings()

    # Configure logging
    setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
    logger.info("Starting Remander")

    # Initialize Tortoise ORM
    config = get_tortoise_config()
    await Tortoise.init(config=config)
    await Tortoise.generate_schemas()
    logger.info("Database initialized")

    # Initialize SAQ worker
    queue = create_queue(settings.redis_url)
    set_queue(queue)
    await queue.connect()
    worker = create_worker(queue)
    worker_task = asyncio.create_task(worker.start())
    logger.info("SAQ worker started")

    yield

    # Shutdown SAQ worker
    worker.stop()
    await worker_task
    await queue.disconnect()
    logger.info("SAQ worker stopped")

    # Shutdown database
    await Tortoise.close_connections()
    logger.info("Remander stopped")


app = FastAPI(title="Remander", version="0.1.0", lifespan=lifespan)

templates = Jinja2Templates(directory="src/remander/templates")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
