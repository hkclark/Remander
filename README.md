# Remander

A home automation app that configures Reolink security cameras for different behavior when "at home" vs "away from home" using the Reolink NVR API. Also controls Tapo smart plugs and Sonoff Mini R2 switches.

See `spec.md` for the full project specification.

## Quick Start

```bash
# Install dependencies
uv sync

# Start Redis (required for job queue)
make redis-up

# Set up the database
make migrate

# Run the app with auto-reload
make run-dev
```

## Reolink API

[Reolink API V8](https://github.com/rgl/reolink-e1-zoom-playground/blob/main/reolink-camera-http-api-user-guide.pdf)

## Database Migrations

Remander uses [Aerich](https://github.com/tortoise/aerich) (Tortoise ORM's migration tool) to manage database schema changes. All schema changes must go through aerich — the app does not auto-create or modify tables on startup.

There are two distinct operations, each with its own make target:

### Applying migrations (fresh install or pulling new code)

```bash
make migrate
```

Runs `aerich upgrade`, which applies all pending migration files in order. Works for:
- **Fresh install**: SQLite creates the database file automatically, aerich applies every migration from scratch
- **Pulling new code**: applies any migration files that aren't in your database yet

### Creating a new migration (after changing a model)

The `DATABASE_URL` in `.env` points to the Docker container path (`/app/data/remander.db`),
which doesn't exist when running locally. To generate migrations outside Docker, use a temp local DB:

```bash
# 1. Make your model changes in src/remander/models/

# 2. Create a local temp DB and apply all existing migrations to it
mkdir -p /tmp/remander_migration
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich upgrade

# 3. Try to generate the migration (this may fail with NotSupportError on SQLite — see note below)
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich migrate --name add_foo_field

# If step 3 failed with "NotSupportError: Alter column comment is unsupported in SQLite",
# use --empty instead to generate a shell with the correct MODELS_STATE, then add SQL manually:
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich migrate --name add_foo_field --empty

# 4. Open the generated file in migrations/models/ and add the SQL to upgrade()/downgrade()

# 5. Apply it to verify the SQL is correct
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich upgrade
```

**Never write migration files by hand** — the `MODELS_STATE` blob must come from aerich's own
tooling. Always use `aerich migrate` (or `aerich migrate --empty`) to get the correct MODELS_STATE,
then add SQL if needed. Manually writing or splitting the MODELS_STATE string corrupts it.

### Applying migrations to an existing system

When pulling code that includes new migration files:

```bash
make migrate
```

This applies any unapplied migrations to the database.

## Plugin System

Remander supports plugins that extend the app with new functionality — routes, templates, dashboard widgets, and SAQ jobs — without modifying the core codebase.

### How It Works

Plugins are standard Python packages discovered via [entry points](https://packaging.python.org/en/latest/specifications/entry-points/). Installing a plugin package (`uv add remander-hot-water`) is all that's needed — no config files or manual registration.

At startup, the app:
1. Discovers all packages declaring `remander.plugins` entry points
2. Calls each entry point factory to get a plugin instance
3. Registers the plugin's routes, templates, SAQ job handlers, and dashboard widgets
4. Runs each plugin's `on_startup()` hook

### Plugin Contract

Every plugin must satisfy the `RemandPlugin` protocol (defined in `src/remander/plugins/base.py`):

| Method | Purpose |
|--------|---------|
| `register_routes(app)` | Add FastAPI routes to the app |
| `register_templates()` | Return absolute path to a template directory (or `None`) |
| `register_jobs()` | Return `(name, handler)` tuples for SAQ job registration |
| `dashboard_widgets()` | Return `DashboardWidget` descriptors for dashboard/guest dashboard |
| `on_startup()` / `on_shutdown()` | Async lifecycle hooks |

### Plugin Data Storage

Plugins store state in the `plugin_data` table — a generic key-value store keyed by `(plugin_name, key)` with JSON values. This avoids plugins needing their own Tortoise models and aerich migrations.

```python
from remander.plugins.data import get_plugin_value, set_plugin_value, delete_plugin_value

await set_plugin_value("my_plugin", "some_key", {"count": 42})
value = await get_plugin_value("my_plugin", "some_key")  # {"count": 42}
await delete_plugin_value("my_plugin", "some_key")
```

### Creating a Plugin

1. Create a package with a `[project.entry-points."remander.plugins"]` entry in `pyproject.toml`
2. The entry point value should be a factory function that returns a `RemandPlugin`-compatible object
3. Use attrs for the plugin class, pydantic-settings for configuration
4. Place templates in a subdirectory named after your plugin (e.g. `templates/my_plugin/`)
5. For development, add the plugin as a uv workspace member

Example `pyproject.toml`:
```toml
[project.entry-points."remander.plugins"]
my_plugin = "my_package:create_plugin"
```

### Workspace Development

During development, plugins live in `plugins/` and are linked as uv workspace members:

```toml
# In the root pyproject.toml
[tool.uv.workspace]
members = ["plugins/*"]

[tool.uv.sources]
remander-hot-water = { workspace = true }
```

Run `uv sync` to install workspace plugins in editable mode.

---

## Hot Water Plugin

The **remander-hot-water** plugin controls a whole-home hot water recirculation pump via a Sonoff Mini R2 switch. It adds a widget to both the main and guest dashboards with duration buttons and a live countdown timer.

### How It Works

1. User taps a duration button (15 / 20 / 30 min) on the dashboard widget
2. The plugin turns on the Sonoff switch and schedules an auto-off SAQ job
3. The widget switches to countdown mode, polling `/hot-water/status` every 5 seconds via HTMX
4. When the timer expires, the SAQ job turns off the switch and clears the timer state
5. If the user cancels early, the switch is turned off immediately and the scheduled job is aborted

### Configuration

Set these environment variables (all prefixed with `PLUGIN_HOT_WATER_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PLUGIN_HOT_WATER_SONOFF_IP` | `192.168.1.50` | IP address of the Sonoff Mini R2 switch |
| `PLUGIN_HOT_WATER_DEFAULT_DURATION_MINUTES` | `20` | Default timer duration |
| `PLUGIN_HOT_WATER_AVAILABLE_DURATIONS` | `[15, 20, 30]` | Duration options shown as buttons |

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/hot-water/status` | Returns HTMX partial with countdown or duration buttons |
| `POST` | `/hot-water/start` | Turns on pump, schedules auto-off (form field: `duration_minutes`) |
| `POST` | `/hot-water/cancel` | Turns off pump, aborts scheduled job |

### Package Structure

```
plugins/remander-hot-water/
├── pyproject.toml
├── src/remander_hot_water/
│   ├── __init__.py          # create_plugin() factory
│   ├── plugin.py            # HotWaterPlugin (implements RemandPlugin)
│   ├── settings.py          # HotWaterSettings (pydantic-settings)
│   ├── routes.py            # FastAPI endpoints
│   ├── service.py           # Business logic (start, cancel, get_status)
│   ├── jobs.py              # SAQ turn-off handler
│   └── templates/hot_water/
│       ├── _dashboard_widget.html
│       ├── _guest_widget.html
│       └── _status_partial.html
└── tests/
    ├── test_service.py
    └── test_routes.py
```

---

## Make Targets

| Target | Description |
|---|---|
| `make run` | Start the app |
| `make run-dev` | Start the app with auto-reload |
| `make redis-up` | Start dev Redis container |
| `make redis-down` | Stop dev Redis container |
| `make test` | Run test suite |
| `make lint` | Run ruff linter |
| `make format` | Format code with ruff |
| `make migrate` | Apply all pending migrations (`aerich upgrade`) |
