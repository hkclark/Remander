"""FastAPI application entrypoint."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader
from starlette.middleware.sessions import SessionMiddleware
from tortoise import Tortoise

from remander.auth import (
    RequiresLoginException,
    get_current_user,
    get_current_user_optional,
    require_admin,
    requires_login_handler,
)
from remander.config import get_settings
from remander.db import get_tortoise_config
from remander.proxy import ProxyPrefixMiddleware
from remander.logging import setup_logging
from remander.plugins.registry import PluginRegistry, set_registry
from remander.services.app_config import load_core_config, load_plugin_config
from remander.worker import create_queue, create_worker, set_queue

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — initialize and tear down resources."""
    settings = get_settings()

    # Assert session secret is configured
    if not settings.session_secret_key:
        raise RuntimeError(
            "SESSION_SECRET_KEY must be set in .env — "
            "generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    # Configure logging from .env defaults (DB not yet available)
    setup_logging(
        log_dir=settings.log_dir,
        log_level=settings.log_level,
        nvr_debug=settings.nvr_debug,
        nvr_debug_max_length=settings.nvr_debug_max_length,
        workflow_debug=settings.workflow_debug,
    )
    logger.info("Starting Remander")

    # Initialize Tortoise ORM
    config = get_tortoise_config()
    await Tortoise.init(config=config)
    logger.info("Database initialized")

    # Load settings from DB (overrides .env defaults) and build plugin config cache
    await load_core_config()
    await load_plugin_config()

    # Reset any commands stuck in RUNNING state from a previous crash or timeout
    from remander.models.command import Command
    from remander.models.enums import CommandStatus

    stale = await Command.filter(status=CommandStatus.RUNNING).update(
        status=CommandStatus.FAILED, error_summary="Process exited while command was running"
    )
    if stale:
        logger.warning("Reset %d stale RUNNING command(s) to FAILED on startup", stale)

    # Discover and register plugins
    registry = PluginRegistry()
    registry.discover()
    set_registry(registry)

    for plugin in registry.plugins:
        plugin.register_routes(app)

    # Build template ChoiceLoader: core templates + plugin template dirs
    global templates
    loaders: list[FileSystemLoader] = [FileSystemLoader("src/remander/templates")]
    for plugin in registry.plugins:
        tpl_dir = plugin.register_templates()
        if tpl_dir:
            loaders.append(FileSystemLoader(tpl_dir))
    templates = Jinja2Templates(env=templates.env)
    templates.env.loader = ChoiceLoader(loaders)

    # Collect plugin job handlers for SAQ worker
    extra_functions = registry.all_job_handlers()

    # Initialize SAQ worker
    queue = create_queue(settings.redis_url)
    set_queue(queue)
    await queue.connect()
    worker = create_worker(queue, extra_functions=extra_functions or None)
    worker_task = asyncio.create_task(worker.start())
    logger.info("SAQ worker started")

    # Run plugin startup hooks
    for plugin in registry.plugins:
        await plugin.on_startup()
        logger.info("Plugin '%s' started", plugin.name)

    yield

    # Run plugin shutdown hooks
    for plugin in registry.plugins:
        await plugin.on_shutdown()
        logger.info("Plugin '%s' stopped", plugin.name)

    # Shutdown SAQ worker
    await worker.stop()
    await worker_task
    await queue.disconnect()
    logger.info("SAQ worker stopped")

    # Shutdown database
    await Tortoise.close_connections()
    logger.info("Remander stopped")


_settings = get_settings()
app = FastAPI(title="Remander", version="0.1.0", lifespan=lifespan)


# Inject current_user into request.state so all templates can read it via request.state.current_user.
# Registered BEFORE SessionMiddleware so it ends up as an inner middleware (runs after the session
# cookie is decoded).
@app.middleware("http")
async def inject_current_user(request: Request, call_next):
    request.state.current_user = await get_current_user_optional(request)
    return await call_next(request)


# Reverse proxy middleware — strips PROXY_PATH_PREFIX from incoming paths and sets root_path.
# Added after SessionMiddleware so it wraps it; SessionMiddleware only reads the cookie header
# and doesn't care about path, so the relative order between them doesn't affect correctness.
app.add_middleware(
    ProxyPrefixMiddleware,
    prefix=_settings.proxy_path_prefix,
    token=_settings.proxy_x_forwarded_token,
    scheme=_settings.proxy_scheme,
)

# Session middleware — must be added before routers are included
# Secret key is validated in lifespan; use a placeholder here for pre-lifespan imports
app.add_middleware(
    SessionMiddleware,
    secret_key=_settings.session_secret_key or "placeholder-replaced-at-startup",
    session_cookie="remander_session",
    https_only=False,
)

# Register the RequiresLoginException handler
app.add_exception_handler(RequiresLoginException, requires_login_handler)  # type: ignore[arg-type]

app.mount("/static", StaticFiles(directory="src/remander/static"), name="static")

templates = Jinja2Templates(directory="src/remander/templates")

from remander.app_colors import PALETTE, hex_color_style  # noqa: E402

templates.env.globals["hex_color_style"] = hex_color_style
templates.env.globals["COLOR_PALETTE"] = PALETTE

# Register routers
from remander.routes.activity import router as activity_router  # noqa: E402
from remander.routes.admin import router as admin_router  # noqa: E402
from remander.routes.auth import router as auth_router  # noqa: E402
from remander.routes.data import router as data_router  # noqa: E402
from remander.routes.bitmasks import router as bitmasks_router  # noqa: E402
from remander.routes.commands import router as commands_router  # noqa: E402
from remander.routes.dashboard import router as dashboard_router  # noqa: E402
from remander.routes.dashboard_buttons import router as dashboard_buttons_router  # noqa: E402
from remander.routes.devices import router as devices_router  # noqa: E402
from remander.routes.guest_dashboard import router as guest_dashboard_router  # noqa: E402
from remander.routes.tags import router as tags_router  # noqa: E402
from remander.routes.users import router as users_router  # noqa: E402

# Public routes — no auth required
app.include_router(dashboard_router)
app.include_router(guest_dashboard_router)
app.include_router(auth_router)
app.include_router(commands_router)  # execute/button and pause-notifications are used from public dashboard

# Protected routes — valid session required
app.include_router(devices_router,            dependencies=[Depends(get_current_user)])
app.include_router(bitmasks_router,           dependencies=[Depends(get_current_user)])
app.include_router(tags_router,               dependencies=[Depends(get_current_user)])
app.include_router(dashboard_buttons_router,  dependencies=[Depends(get_current_user)])
app.include_router(activity_router,           dependencies=[Depends(get_current_user)])
app.include_router(admin_router,              dependencies=[Depends(get_current_user)])

# Admin-only routes
app.include_router(users_router,              dependencies=[Depends(require_admin)])
app.include_router(data_router,               dependencies=[Depends(require_admin)])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
