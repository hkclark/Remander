# Milestone 1: Foundation & Project Setup

**Goal**: Everything needed before business logic begins.

**Exit criteria**: `make dev` starts the app, `make test` runs (empty) tests, database tables are
created via migration, health-check returns 200.

**Status**: Complete

---

## Tasks

### 1. Project Scaffolding
- [x] Initialize project with `uv init`
- [x] Configure `pyproject.toml` (name, version, Python 3.14, dependencies)
- [x] Create directory structure:
  ```
  src/
    remander/
      __init__.py
      main.py
      config.py
      db.py
      logging.py
      models/
        __init__.py
        enums.py
        device.py
        tag.py
        bitmask.py
        detection.py
        command.py
        activity.py
        state.py
      routes/
        __init__.py
      services/
        __init__.py
      clients/
        __init__.py
      workflows/
        __init__.py
      templates/
  ```
- [x] Add all dependencies to `pyproject.toml`:
  - fastapi, uvicorn, jinja2, python-multipart
  - tortoise-orm, aerich
  - pydantic, pydantic-settings
  - pydantic-ai, pydantic-graph
  - saq, redis
  - reolink-aio, python-kasa, httpx
  - astral, aiosmtplib
  - attrs
  - ruff (dev)
  - pytest, pytest-asyncio (dev)
- [x] Run `uv sync` to generate `uv.lock`

### 2. Configuration
- [x] Create `src/remander/config.py` with pydantic-settings `Settings` class
- [x] All settings from spec Section 5 (NVR, Redis, DB, SMTP, lat/long, logging, PUID/PGID, power-on timing)
- [x] Create `.env.example` with documented defaults

### 3. Docker
- [x] Create `Dockerfile` (Python 3.14-slim, uv, configurable UID/GID)
- [x] Create `docker-compose.yml` (app + Redis containers, volumes for data/logs)
- [x] Create `.dockerignore` (`.git`, `__pycache__`, `.env`, etc.)

### 4. Database Models
- [x] Create `src/remander/models/enums.py` — all StrEnum types from spec Section 6
  - DeviceType, DeviceBrand, PowerDeviceSubtype, DetectionType
  - HourBitmaskSubtype, Mode, CommandType, CommandStatus, ActivityStatus
- [x] Create `src/remander/models/device.py` — Device model
- [x] Create `src/remander/models/tag.py` — Tag model (with ManyToMany to Device via device_tag)
- [x] Create `src/remander/models/bitmask.py` — HourBitmask, ZoneMask, DeviceBitmaskAssignment models
- [x] Create `src/remander/models/detection.py` — DeviceDetectionType model
- [x] Create `src/remander/models/command.py` — Command model
- [x] Create `src/remander/models/activity.py` — ActivityLog model
- [x] Create `src/remander/models/state.py` — SavedDeviceState and AppState models
- [x] Register all models in `src/remander/models/__init__.py`

### 5. Database Setup (Tortoise ORM + Aerich)
- [x] Configure Tortoise ORM in FastAPI app (lifespan)
- [x] Create `TORTOISE_ORM` config dict for Aerich in `src/remander/db.py`
- [x] Initialize Aerich (`aerich init`, `aerich init-db`)
- [x] Verify migrations create all tables from spec Section 6

### 6. Logging
- [x] Create `src/remander/logging.py` — logging setup function
- [x] Dual output: stdout + file (`LOG_DIR/remander.log`)
- [x] Configurable log level from settings
- [x] TimedRotatingFileHandler (weekly rotation)
- [x] Structured format: `%(asctime)s %(levelname)s %(name)s %(message)s`

### 7. FastAPI App
- [x] Create `src/remander/main.py` — FastAPI app with lifespan
- [x] Lifespan: initialize Tortoise ORM, configure logging
- [x] Health-check endpoint: `GET /health` returns `{"status": "ok"}`
- [x] Mount Jinja2 templates directory

### 8. Makefile
- [x] `dev` — `docker compose up --build`
- [x] `prod` — `docker compose up -d`
- [x] `test` — `uv run pytest`
- [x] `lint` — `uv run ruff check .`
- [x] `format` — `uv run ruff format .`
- [x] `migrate` — `uv run aerich migrate && uv run aerich upgrade`
- [x] `logs` — `docker compose logs -f app`

### 9. Ruff Configuration
- [x] Add `[tool.ruff]` section to `pyproject.toml`
- [x] Line length: 100
- [x] Black-compatible formatting
- [x] isort import sorting
- [x] Target Python 3.14
- [x] Exclude migrations from linting

### 10. Test Infrastructure
- [x] Create `tests/` directory
- [x] Create `tests/conftest.py` with:
  - Async test configuration (pytest-asyncio)
  - Tortoise ORM test database setup/teardown (in-memory SQLite)
  - `AsyncClient` fixture for FastAPI test client
- [x] Create `tests/test_health.py` — verify health-check returns 200
- [x] Create `tests/factories/` directory with `__init__.py` (empty, ready for Milestone 2)
- [x] Verify `make test` passes

### 11. Final Verification
- [x] `make lint` passes with no errors
- [x] `make format` produces no changes
- [x] `make test` passes (health-check test)
- [ ] `make dev` starts the app and Redis containers *(requires .env with real NVR credentials)*
- [x] `GET /health` returns 200 (verified via test client)
- [x] Database tables are created on startup (all 11 tables verified)

---

# Milestone 2: Core Backend — Devices, Bitmasks, Hardware

**Goal**: CRUD operations and hardware integration (no commands or workflows yet).

**Exit criteria**: All device/bitmask/tag CRUD works end-to-end. NVR, Tapo, and Sonoff clients
have passing tests (mocked hardware). Dynamic bitmask calculation produces correct results.

**Status**: Pending

---

## Tasks

### 1. Device Service
- [ ] Create `src/remander/services/device.py`
- [ ] `create_device(...)` — create a camera or power device with all fields from spec Section 6
- [ ] `get_device(id)` — fetch a device by ID, with related tags and detection types
- [ ] `list_devices(device_type=None, is_enabled=None)` — list/filter devices
- [ ] `update_device(id, ...)` — update device fields
- [ ] `delete_device(id)` — delete a device (cascade to detection types, bitmask assignments, tags)
- [ ] `set_power_device(camera_id, power_device_id)` — associate a camera with its power device
- [ ] `get_cameras_with_power_devices()` — list cameras that have associated power devices
- [ ] Tests: `tests/test_device_service.py`

### 2. Tag Service
- [ ] Create `src/remander/services/tag.py`
- [ ] `create_tag(name)` — create a tag
- [ ] `list_tags()` — list all tags with device counts
- [ ] `delete_tag(id)` — delete a tag
- [ ] `add_tag_to_device(device_id, tag_id)` — assign a tag to a device
- [ ] `remove_tag_from_device(device_id, tag_id)` — remove a tag from a device
- [ ] `get_devices_by_tag(tag_name)` — fetch all devices with a given tag
- [ ] Tests: `tests/test_tag_service.py`

### 3. Detection Type Service
- [ ] Create `src/remander/services/detection.py`
- [ ] `set_detection_types(device_id, detection_types: list[DetectionType])` — bulk set which types a device supports
- [ ] `enable_detection_type(device_id, detection_type)` — enable a specific type
- [ ] `disable_detection_type(device_id, detection_type)` — disable a specific type
- [ ] `get_enabled_detection_types(device_id)` — list enabled detection types for a device
- [ ] Tests: `tests/test_detection_service.py`

### 4. Bitmask Service
- [ ] Create `src/remander/services/bitmask.py`
- [ ] **Hour Bitmask CRUD**:
  - [ ] `create_hour_bitmask(name, subtype, ...)` — create static or dynamic bitmask
  - [ ] `get_hour_bitmask(id)` — fetch by ID
  - [ ] `list_hour_bitmasks()` — list all
  - [ ] `update_hour_bitmask(id, ...)` — update
  - [ ] `delete_hour_bitmask(id)` — delete
- [ ] **Zone Mask CRUD**:
  - [ ] `create_zone_mask(name, mask_value)` — create (validate 4800-char string of 0s and 1s)
  - [ ] `get_zone_mask(id)` — fetch by ID
  - [ ] `list_zone_masks()` — list all
  - [ ] `update_zone_mask(id, ...)` — update
  - [ ] `delete_zone_mask(id)` — delete
- [ ] **Bitmask Assignment CRUD**:
  - [ ] `assign_bitmask(device_id, mode, detection_type, hour_bitmask_id, zone_mask_id)` — create or update assignment
  - [ ] `get_assignments_for_device(device_id, mode=None)` — list assignments for a device
  - [ ] `delete_assignment(id)` — remove an assignment
- [ ] **Bitmask Resolution**:
  - [ ] `resolve_hour_bitmask(hour_bitmask, date=None)` — return the 24-char value (static: return value directly; dynamic: calculate from sunrise/sunset)
  - [ ] `resolve_bitmasks_for_device(device_id, mode)` — return resolved hour bitmask + zone mask per detection type for a device in a given mode
- [ ] Tests: `tests/test_bitmask_service.py`

### 5. Sunrise/Sunset Calculation
- [ ] Create `src/remander/services/solar.py`
- [ ] `get_sunrise_sunset(latitude, longitude, date=None)` — return sunrise/sunset times using astral
- [ ] `compute_dynamic_bitmask(sunrise, sunset, sunrise_offset_minutes, sunset_offset_minutes, fill_value)` — build a 24-char bitmask from sunrise/sunset times (rounded to nearest hour)
- [ ] Tests: `tests/test_solar_service.py`
  - [ ] Test with known lat/long and date for predictable sunrise/sunset
  - [ ] Test offset handling (positive and negative)
  - [ ] Test fill_value="1" (daytime active) and fill_value="0" (nighttime active)
  - [ ] Test edge cases: midnight crossings, polar regions (if applicable)

### 6. Reolink NVR Client
- [ ] Create `src/remander/clients/reolink.py`
- [ ] `ReolinkNVRClient` class wrapping reolink-aio
  - [ ] `login()` — authenticate with the NVR
  - [ ] `logout()` — close the session
  - [ ] `list_channels()` — return list of connected cameras with metadata
  - [ ] `get_channel_info(channel)` — get detailed info for one camera
  - [ ] `get_alarm_schedule(channel, detection_type)` — get current notification bitmask (may need direct HTTP API)
  - [ ] `set_alarm_schedule(channel, detection_type, hour_bitmask)` — set notification bitmask
  - [ ] `get_detection_zones(channel, detection_type)` — get current zone mask
  - [ ] `set_detection_zones(channel, detection_type, zone_mask)` — set zone mask
  - [ ] `move_to_preset(channel, preset_index, speed)` — PTZ move to preset
  - [ ] `is_channel_online(channel)` — check if a camera channel is online
- [ ] Investigate reolink-aio API coverage vs. direct HTTP calls needed
- [ ] Tests: `tests/test_reolink_client.py` (mocked — no real NVR needed)

### 7. Tapo Power Client
- [ ] Create `src/remander/clients/tapo.py`
- [ ] `TapoClient` class wrapping python-kasa
  - [ ] `turn_on(ip_address)` — power on the plug
  - [ ] `turn_off(ip_address)` — power off the plug
  - [ ] `is_on(ip_address)` — check current power state
- [ ] Tests: `tests/test_tapo_client.py` (mocked python-kasa)

### 8. Sonoff Mini R2 Client
- [ ] Create `src/remander/clients/sonoff.py`
- [ ] `SonoffClient` class using httpx
  - [ ] `turn_on(ip_address)` — POST to /zeroconf/switch with `{"data": {"switch": "on"}}`
  - [ ] `turn_off(ip_address)` — POST to /zeroconf/switch with `{"data": {"switch": "off"}}`
  - [ ] `is_on(ip_address)` — POST to /zeroconf/info, parse switch state from response
- [ ] Tests: `tests/test_sonoff_client.py` (mocked httpx)

### 9. Test Factories
- [ ] Create `tests/factories/device.py` — factory for Device with sensible defaults
- [ ] Create `tests/factories/tag.py` — factory for Tag
- [ ] Create `tests/factories/bitmask.py` — factories for HourBitmask, ZoneMask
- [ ] Create `tests/factories/command.py` — factory for Command (needed for SavedDeviceState tests)
- [ ] Update `tests/factories/__init__.py` with imports

### 10. Final Verification
- [ ] All new tests pass (`make test`)
- [ ] `make lint` passes with no errors
- [ ] `make format` produces no changes
- [ ] Device CRUD: create, read, update, delete cameras and power devices
- [ ] Tag CRUD: create, list, delete tags; assign/remove from devices
- [ ] Detection types: set, enable, disable per device
- [ ] Bitmask CRUD: create static/dynamic hour bitmasks, zone masks, assignments
- [ ] Dynamic bitmask: sunrise/sunset calculation produces correct 24-char values
- [ ] Bitmask resolution: resolves correct values per device + mode + detection type
- [ ] NVR client: all methods tested with mocked reolink-aio
- [ ] Tapo client: on/off/status tested with mocked python-kasa
- [ ] Sonoff client: on/off/status tested with mocked httpx
