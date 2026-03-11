# Remander

A home automation app that configures Reolink security cameras for different behavior when "at home" vs "away from home" using the Reolink NVR API. Also controls Tapo smart plugs and Sonoff Mini R2 switches.

See `spec.md` for the full project specification. Detailed design docs live in `docs/`.

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

## Authentication & First-Run Setup

### Required: session secret key

Before starting the app you must set `SESSION_SECRET_KEY` in `.env`. The app refuses to start without it.

```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_hex(32))"
```

Add it to `.env`:

```env
SESSION_SECRET_KEY=<the generated value>
```

### First-run setup (`/setup`)

On a fresh install with no users, visiting `/login` automatically redirects to `/setup`. This is a one-time bootstrap page for creating the first administrator account.

1. Navigate to `http://localhost:8000/setup` (or `/login` — it redirects there automatically)
2. Enter an email address, an optional display name, and a password (minimum 8 characters)
3. Click **Create Admin Account**
4. You're redirected to `/login` — sign in with the credentials you just created

Once any user exists, `/setup` returns **404** permanently. It is not possible to accidentally re-run setup on a populated database.

### User management

After the first admin account exists, additional users are managed at **Admin → Users** (`/admin/users`):

- **Invite a user** — enter their email address; they receive a time-limited invitation link (valid 7 days) to set their own password
- **Toggle active/admin** — activate/deactivate accounts and grant or revoke admin privileges
- **Resend invite** — if the invitation link has expired, generate a new one
- **View history** — see a log of login events (method, IP address, timestamp) for each user

Password reset is available to all users via `/forgot-password` — they receive an email with a reset link (valid 1 hour).

### Token-based dashboard access

The main dashboard (`/`) accepts an optional `?token=` query parameter. This allows embedding a direct link in a home automation system (e.g., Home Assistant) that pre-authenticates a specific user without requiring a browser session. Token values are managed per-user in Admin → Users.

---

## Configuration

Most settings are managed through the admin UI at **Admin → Settings** (`/admin/settings`) — no `.env` editing needed after initial setup.

### Bootstrap settings (`.env` only)

Two settings must remain in `.env` because the app needs them before the database is available:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:////app/data/remander.db` | SQLite path (or PostgreSQL URL) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL for the job queue |

These are shown read-only on the Settings page but cannot be changed there.

### Web UI settings

Everything else — NVR credentials, SMTP settings, guest dashboard PIN, plugin settings — is configurable via the Settings page. Changes take effect immediately in the running process (no restart required), except for `log_level` which shows a "restart required" badge.

**How it works:**

At startup the app:
1. Reads `Settings` from `.env` / env vars as usual (pydantic-settings)
2. Loads any overrides stored in the `app_config` database table
3. Merges the DB values on top, caches the result as the live settings instance
4. `get_settings()` everywhere in the app returns this cached instance

When a value is saved via the admin UI, the DB row is updated and the cache is rebuilt — the new value is immediately live.

**Secret fields** (passwords, PINs) are shown as `••••••` on the settings page. Submitting the form with an empty password field does **not** overwrite the stored value — only a non-empty submission updates it.

### Settings groups

| Group | Configurable fields |
|-------|---------------------|
| NVR | host, port, username, password, HTTPS, timeout |
| Email Notifications | SMTP host/port/credentials, from/to addresses, TLS |
| Location | latitude, longitude (used for sunrise/sunset bitmasks) |
| Guest Dashboard | show-mode toggle, PIN |
| Advanced | debug, log level ⟳, power-on timing, job timeout |

`⟳` = requires restart

---

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
| `settings_fields()` | Return `SettingField` descriptors so the admin UI can render a settings form for this plugin |
| `on_startup()` / `on_shutdown()` | Async lifecycle hooks |

`SettingField` is an attrs class that declares a single configurable value:

```python
@attrs.define
class SettingField:
    key: str               # field name, e.g. "sonoff_ip"
    label: str             # human-readable, e.g. "Sonoff Switch IP Address"
    description: str = ""
    field_type: str = "string"  # "string" | "int" | "bool" | "float" | "list_int"
    default: Any = None
    secret: bool = False          # renders as a password input with reveal toggle
    restart_required: bool = False
```

### Plugin Data Storage

Plugins store state in the `plugin_data` table — a generic key-value store keyed by `(plugin_name, key)` with JSON values. This avoids plugins needing their own Tortoise models and aerich migrations.

```python
from remander.plugins.data import get_plugin_value, set_plugin_value, delete_plugin_value

await set_plugin_value("my_plugin", "some_key", {"count": 42})
value = await get_plugin_value("my_plugin", "some_key")  # {"count": 42}
await delete_plugin_value("my_plugin", "some_key")
```

### Plugin Settings

Plugin settings are stored in the `app_config` database table (see **Configuration** below) under the namespace `plugin.{plugin_name}.{key}`. At runtime, plugins read their live values via:

```python
from remander.services.app_config import get_plugin_setting, set_plugin_setting

# Sync read from in-memory cache (populated at startup)
ip = get_plugin_setting("my_plugin", "device_ip", default="192.168.1.10")

# Async write — persists to DB and refreshes the cache
await set_plugin_setting("my_plugin", "device_ip", "10.0.0.5")
```

The admin UI at `/admin/settings` automatically renders a settings form for each plugin that declares `settings_fields()`.

### Creating a Plugin

1. Create a package with a `[project.entry-points."remander.plugins"]` entry in `pyproject.toml`
2. The entry point value should be a factory function that returns a `RemandPlugin`-compatible object
3. Use attrs for the plugin class; declare settings via `settings_fields()` rather than pydantic-settings
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

Hot water settings are managed through the admin UI at **Admin → Settings → Hot Water Plugin**. No `.env` changes are needed.

| Setting | Default | Description |
|---------|---------|-------------|
| Sonoff Switch IP Address | `192.168.1.50` | IP of the Sonoff Mini R2 switch |
| Default Duration (minutes) | `20` | Timer duration pre-selected in the widget |
| Available Durations | `15, 20, 30` | Duration buttons shown in the widget |

Changes take effect immediately — no restart required.

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

## Design Docs

| File | What it covers |
|------|---------------|
| [`docs/plugin-architecture.md`](docs/plugin-architecture.md) | Plugin discovery, `RemandPlugin` protocol, `DashboardWidget`, `SettingField`, `PluginRegistry`, template namespacing, `plugin_data` storage |
| [`docs/configuration.md`](docs/configuration.md) | `AppConfig` table, settings cache overlay, plugin config cache, admin UI design, secret field UX |
| [`docs/authentication.md`](docs/authentication.md) | Session auth, password reset, user invitations, token-based dashboard access, command attribution, access history |

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
