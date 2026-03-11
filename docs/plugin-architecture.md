# Plugin Architecture

Remander supports first-party and third-party plugins that add routes, templates, dashboard widgets,
SAQ job handlers, and configurable settings — without touching the core codebase.

---

## Discovery

Plugins are standard Python packages. They declare themselves via a
[Python entry point](https://packaging.python.org/en/latest/specifications/entry-points/)
in their `pyproject.toml`:

```toml
[project.entry-points."remander.plugins"]
hot_water = "remander_hot_water:create_plugin"
```

The value must be a **zero-argument factory function** that returns a `RemandPlugin`-compatible
object. At startup, `PluginRegistry.discover()` calls
`importlib.metadata.entry_points(group="remander.plugins")`, loads each factory, instantiates it,
and registers the result.

---

## The `RemandPlugin` Protocol

Defined in `src/remander/plugins/base.py` as a `@runtime_checkable Protocol`. Every plugin must
implement all of these:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `register_routes` | `(app: FastAPI) -> None` | Call `app.include_router(...)` to add routes |
| `register_templates` | `() -> str \| None` | Return absolute path to a template directory, or `None` |
| `register_jobs` | `() -> list[tuple[str, Callable]]` | Return `(job_name, handler_fn)` pairs for SAQ |
| `dashboard_widgets` | `() -> list[DashboardWidget]` | Widgets to inject into dashboards |
| `settings_fields` | `() -> list[SettingField]` | Configurable settings to expose in the admin UI |
| `on_startup` | `async () -> None` | Run after the app is fully initialized |
| `on_shutdown` | `async () -> None` | Run before the app tears down |

Attributes `name: str` and `version: str` are also required.

Use `attrs.define` for the plugin class:

```python
@attrs.define
class HotWaterPlugin:
    name: str = "hot_water"
    version: str = "0.1.0"

    def register_routes(self, app: FastAPI) -> None:
        from remander_hot_water.routes import router
        app.include_router(router)

    def register_templates(self) -> str | None:
        return str(Path(__file__).resolve().parent / "templates")

    def register_jobs(self) -> list[tuple[str, Callable]]:
        from remander_hot_water.jobs import turn_off_hot_water
        return [("turn_off_hot_water", turn_off_hot_water)]

    def dashboard_widgets(self) -> list[DashboardWidget]:
        return [DashboardWidget(plugin_name=self.name, template_name="hot_water/_widget.html", target="dashboard")]

    def settings_fields(self) -> list[SettingField]:
        return [SettingField(key="sonoff_ip", label="Sonoff Switch IP Address")]

    async def on_startup(self) -> None: pass
    async def on_shutdown(self) -> None: pass
```

---

## Descriptor Classes

### `DashboardWidget`

```python
@attrs.define
class DashboardWidget:
    plugin_name: str
    template_name: str   # namespaced, e.g. "hot_water/_widget.html"
    target: str          # "dashboard" or "guest_dashboard"
    sort_order: int = 100
```

Widgets are collected by `PluginRegistry.all_dashboard_widgets(target)` and injected into the
relevant dashboard templates. Templates must be namespaced under a subdirectory matching the plugin
name to prevent collisions.

### `SettingField`

```python
@attrs.define
class SettingField:
    key: str                       # DB key suffix, e.g. "sonoff_ip"
    label: str                     # Human-readable label
    description: str = ""
    field_type: str = "string"     # "string" | "int" | "bool" | "float" | "list_int"
    default: Any = None
    secret: bool = False           # Renders as password input; empty submit = no-op
    restart_required: bool = False # Shows a "restart" badge in the admin UI
```

The admin UI at `/admin/settings` renders a form section for each plugin that returns a non-empty
`settings_fields()` list. Settings are stored in the `app_config` table under the key
`plugin.{plugin_name}.{field.key}` and read back via the in-memory plugin config cache.

---

## `PluginRegistry`

Defined in `src/remander/plugins/registry.py`. A module-level singleton managed by
`get_registry()` / `set_registry()` (same pattern as the SAQ queue singleton).

```python
registry = get_registry()

registry.plugins                           # list[RemandPlugin]
registry.get("hot_water")                  # RemandPlugin | None
registry.all_dashboard_widgets("dashboard") # sorted by sort_order
registry.all_job_handlers()                # list[(name, fn)] for SAQ worker
registry.all_settings_fields()             # dict[plugin_name, list[SettingField]]
```

`discover()` is called once during the FastAPI lifespan, before routes or workers are started.

---

## Lifespan Integration

In `src/remander/main.py`, the plugin lifecycle runs in this order during startup:

1. DB initialized, settings overlay loaded
2. `registry.discover()` — load all plugins from entry points
3. For each plugin: `plugin.register_routes(app)` — add routes to the running FastAPI app
4. Build `Jinja2 ChoiceLoader`: core templates dir + each plugin's `register_templates()` path
5. Collect `registry.all_job_handlers()` and pass to `create_worker()`
6. For each plugin: `await plugin.on_startup()`

And during shutdown (reverse order):

1. For each plugin: `await plugin.on_shutdown()`
2. SAQ worker stopped
3. DB connections closed

---

## Template Namespacing

Plugins place their templates in a subdirectory named after themselves:

```
src/remander_hot_water/templates/
└── hot_water/                    ← plugin name as subdirectory
    ├── _dashboard_widget.html
    ├── _guest_widget.html
    └── _status_partial.html
```

The `Jinja2 ChoiceLoader` chains core templates first, then plugin template directories. This means:
- Plugin templates are resolved as `"hot_water/_status_partial.html"` — the subdirectory prefix
  prevents name collisions between plugins and with core templates.
- Core templates take precedence over plugin templates if names ever clash.

---

## Plugin Data Storage

Plugins that need to persist runtime state (not configuration) use the `plugin_data` table — a
generic `(plugin_name, key) → JSON value` store that avoids requiring per-plugin migrations:

```python
from remander.plugins.data import get_plugin_value, set_plugin_value, delete_plugin_value

await set_plugin_value("hot_water", "timer_state", {"end_time": "...", "job_id": "abc"})
state = await get_plugin_value("hot_water", "timer_state")  # or None
await delete_plugin_value("hot_water", "timer_state")
```

This is distinct from **plugin settings** (user-configurable values managed via `app_config` and the
admin UI). Use `plugin_data` for transient runtime state; use `AppConfig` for configuration.

---

## Development Workflow

For in-repo plugin development, use a uv workspace:

```toml
# root pyproject.toml
[tool.uv.workspace]
members = ["plugins/*"]

[tool.uv.sources]
remander-hot-water = { workspace = true }
```

Run `uv sync` to install all workspace plugins in editable mode. The entry point is registered
via the plugin package's own `pyproject.toml`, so `discover()` finds it automatically.

### Testing plugins

Plugin tests live in `plugins/{name}/tests/`. The plugin's `conftest.py` should **not** have an
`__init__.py` in the test directory (this causes module name collisions with the root conftest).

For tests that exercise admin routes involving plugin registry lookups, manually register the
plugin in a fixture:

```python
@pytest.fixture(autouse=True)
def _setup_registry():
    from remander.plugins.registry import PluginRegistry, set_registry
    from remander_hot_water.plugin import HotWaterPlugin

    registry = PluginRegistry()
    registry.register(HotWaterPlugin())
    set_registry(registry)
    yield
    set_registry(None)
```
