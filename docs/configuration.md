# Configuration System

Remander's configuration is split into two tiers: a small set of **bootstrap settings** that must
live in `.env`, and everything else managed through the **admin UI** and stored in the database.

---

## Why Two Tiers?

`DATABASE_URL` and `REDIS_URL` must be known before the app can connect to a database. There is no
safe way to store them in the database — the chicken-and-egg problem. Everything else can move to
the DB once those two connections are established.

Both bootstrap settings have hardcoded Docker-path defaults in `config.py` so a fresh install works
with an empty `.env`.

---

## Storage: The `app_config` Table

A single `AppConfig` Tortoise model (`src/remander/models/app_config.py`) stores all non-bootstrap
settings:

```python
class AppConfig(Model):
    key = CharField(max_length=200, primary_key=True)
    value = JSONField()       # wrapped as {"_v": actual_value} — see note below
    updated_at = DatetimeField(auto_now=True)

    class Meta:
        table = "app_config"
```

### Key namespace

| Pattern | Example | Used for |
|---------|---------|----------|
| `{field_name}` | `nvr_host`, `smtp_port` | Core `Settings` fields |
| `plugin.{name}.{field}` | `plugin.hot_water.sonoff_ip` | Plugin settings |

### JSON wrapping quirk

Tortoise's `JSONField.to_python_value()` treats Python `str` inputs as pre-encoded JSON and calls
`orjson.loads()` on them — so storing `"192.168.1.100"` directly fails. All values are therefore
wrapped in `{"_v": actual_value}` at the service layer. This is transparent to callers of the
service functions.

---

## Service Layer

`src/remander/services/app_config.py` provides:

### Low-level CRUD

```python
# Read a single value; returns `default` if not found
value = await get_config_value("nvr_host", default="localhost")

# Upsert
await set_config_value("nvr_host", "10.0.0.1")

# Delete; returns True if the key existed
deleted = await delete_config_value("nvr_host")

# Read all core (non-plugin) keys, or all plugin.* keys
core = await get_all_config(prefix=None)       # excludes plugin.* keys
plugin = await get_all_config(prefix="plugin.") # only plugin.* keys
```

### Core settings cache

```python
# Called once during lifespan after DB init.
# Reads Settings() from .env, merges DB overrides on top, caches the result.
await load_core_config()
```

After `load_core_config()`, every `get_settings()` call returns the merged, cached instance. When
a value is saved via the admin UI, `load_core_config()` is called again to rebuild the cache.

Unknown DB keys (from removed settings) are silently ignored so old rows don't break the app.

### Plugin config cache

```python
# Called once during lifespan after load_core_config().
# Populates an in-memory dict: {plugin_name: {field: value, ...}, ...}
await load_plugin_config()

# Sync read from the in-memory cache — safe to call anywhere
ip = get_plugin_setting("hot_water", "sonoff_ip", default="192.168.1.50")

# Async write — persists to AppConfig and refreshes the in-memory cache
await set_plugin_setting("hot_water", "sonoff_ip", "10.0.0.5")
```

---

## Core Settings Cache (`config.py`)

`Settings` (pydantic-settings) is no longer instantiated on every `get_settings()` call.
Instead, a module-level `_cached_settings` is populated during lifespan:

```
.env / env vars  →  Settings()  →  DB overlay (load_core_config)  →  _cached_settings
                                                                           ↑
                                                              get_settings() returns this
```

```python
# config.py
_cached_settings: Settings | None = None

def get_settings() -> Settings:
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()   # cold-start fallback (tests, pre-lifespan)
    return _cached_settings

def set_settings(settings: Settings) -> None:
    global _cached_settings
    _cached_settings = settings
```

`set_settings()` is used by:
- `load_core_config()` — to install the DB-merged instance after startup
- Tests — to inject a known `Settings` instance without re-reading `.env`

---

## Lifespan Order

In `src/remander/main.py`:

```python
# DB initialized first
await Tortoise.init(config=get_tortoise_config())

# Then settings overlay
await load_core_config()    # merges DB on top of .env Settings, caches result
await load_plugin_config()  # populates plugin config cache from plugin.* AppConfig rows
settings = get_settings()   # now returns the merged instance

# Plugin discovery uses get_plugin_setting() internally via _get_settings() helpers
registry = PluginRegistry()
registry.discover()
```

---

## Admin UI

**Route:** `GET /admin/settings` — rendered by `src/remander/templates/admin/settings.html`

The page is divided into sections:

| Section | Save endpoint |
|---------|--------------|
| NVR | `POST /admin/settings/core/nvr` |
| Email Notifications | `POST /admin/settings/core/email` |
| Location | `POST /admin/settings/core/location` |
| Guest Dashboard | `POST /admin/settings/core/guest_dashboard` |
| Advanced | `POST /admin/settings/core/advanced` |
| Per-plugin (one per plugin with `settings_fields()`) | `POST /admin/settings/plugin/{plugin_name}` |
| Read-only (`.env` only) | — |

Each section saves independently via HTMX (no full-page reload) and shows a toast notification on
success. The response from each save endpoint is `admin/_settings_toast.html`, which uses HTMX
OOB swap (`hx-swap-oob="beforeend:#toast-container"`) to inject the toast.

### Core settings groups

Groups are defined as a list of `SettingsGroup` objects in `src/remander/routes/admin.py`:

```python
SettingsGroup(id="nvr", title="NVR", fields=[
    SettingsField("nvr_host", "Host"),
    SettingsField("nvr_port", "Port", field_type="int"),
    SettingsField("nvr_password", "Password", field_type="password", secret=True),
    ...
])
```

### Secret field UX

Password and PIN fields follow this contract:

- **Page load**: always rendered as empty (value is never sent to the browser)
- **Submit with empty field**: the stored value is **not** overwritten — skip silently
- **Submit with non-empty field**: the new value is stored
- **Reveal toggle**: an eye-icon button switches the input between `type="password"` and
  `type="text"` for in-place reveal without JavaScript frameworks

### Plugin settings

The admin UI discovers plugin settings sections dynamically via
`registry.all_settings_fields()`. Each plugin that implements `settings_fields()` with at least
one field gets its own collapsible section. The `list_int` field type renders as a comma-separated
text input (e.g. `15,20,30`), which the save handler splits and coerces back to `list[int]`.

### Read-only section

Settings that must stay in `.env` (`database_url`, `redis_url`, `puid`, `pgid`, `nvr_debug`,
`nvr_debug_max_length`, `workflow_debug`) are shown in a read-only display using their current
in-memory values. No save button is rendered for these.

---

## Bootstrap Settings (`.env`)

The minimum `.env` for a working install is actually empty — the app starts with no `.env` at all.
`DATABASE_URL` and `REDIS_URL` default to Docker container paths, and all other settings (including
NVR credentials) can be configured via **Admin → Settings** after first boot.

If you prefer to set NVR credentials in `.env` (as a base layer that the UI can later override):

```env
NVR_HOST=192.168.1.100
NVR_USERNAME=admin
NVR_PASSWORD=yourpassword
```

`nvr_host`, `nvr_username`, and `nvr_password` all default to empty strings. If they are empty
when a workflow runs, the NVR connection will fail at that point with a connection error — the app
does not validate credentials at startup.
