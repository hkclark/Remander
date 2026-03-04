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

**Methodology**: Red/green TDD — write failing tests first, then implement to make them pass.

**Status**: Complete

---

## Tasks

### 1. Test Factories
- [x] Create `tests/factories/device.py` — factory for Device with sensible defaults
- [x] Create `tests/factories/tag.py` — factory for Tag
- [x] Create `tests/factories/bitmask.py` — factories for HourBitmask, ZoneMask
- [x] Create `tests/factories/command.py` — factory for Command (needed for SavedDeviceState tests)
- [x] Update `tests/factories/__init__.py` with imports

### 2. Device Service

**RED** — Write failing tests (`tests/test_device_service.py`):
- [x] Test `create_device(...)` — create a camera or power device with all fields from spec Section 6
- [x] Test `get_device(id)` — fetch a device by ID, with related tags and detection types
- [x] Test `list_devices(device_type=None, is_enabled=None)` — list/filter devices
- [x] Test `update_device(id, ...)` — update device fields
- [x] Test `delete_device(id)` — delete a device (cascade to detection types, bitmask assignments, tags)
- [x] Test `set_power_device(camera_id, power_device_id)` — associate a camera with its power device
- [x] Test `get_cameras_with_power_devices()` — list cameras that have associated power devices

**GREEN** — Implement (`src/remander/services/device.py`):
- [x] `create_device(...)` — make tests pass
- [x] `get_device(id)` — make tests pass
- [x] `list_devices(device_type=None, is_enabled=None)` — make tests pass
- [x] `update_device(id, ...)` — make tests pass
- [x] `delete_device(id)` — make tests pass
- [x] `set_power_device(camera_id, power_device_id)` — make tests pass
- [x] `get_cameras_with_power_devices()` — make tests pass

### 3. Tag Service

**RED** — Write failing tests (`tests/test_tag_service.py`):
- [x] Test `create_tag(name)` — create a tag
- [x] Test `list_tags()` — list all tags with device counts
- [x] Test `delete_tag(id)` — delete a tag
- [x] Test `add_tag_to_device(device_id, tag_id)` — assign a tag to a device
- [x] Test `remove_tag_from_device(device_id, tag_id)` — remove a tag from a device
- [x] Test `get_devices_by_tag(tag_name)` — fetch all devices with a given tag

**GREEN** — Implement (`src/remander/services/tag.py`):
- [x] `create_tag(name)` — make tests pass
- [x] `list_tags()` — make tests pass
- [x] `delete_tag(id)` — make tests pass
- [x] `add_tag_to_device(device_id, tag_id)` — make tests pass
- [x] `remove_tag_from_device(device_id, tag_id)` — make tests pass
- [x] `get_devices_by_tag(tag_name)` — make tests pass

### 4. Detection Type Service

**RED** — Write failing tests (`tests/test_detection_service.py`):
- [x] Test `set_detection_types(device_id, detection_types: list[DetectionType])` — bulk set which types a device supports
- [x] Test `enable_detection_type(device_id, detection_type)` — enable a specific type
- [x] Test `disable_detection_type(device_id, detection_type)` — disable a specific type
- [x] Test `get_enabled_detection_types(device_id)` — list enabled detection types for a device

**GREEN** — Implement (`src/remander/services/detection.py`):
- [x] `set_detection_types(device_id, ...)` — make tests pass
- [x] `enable_detection_type(device_id, detection_type)` — make tests pass
- [x] `disable_detection_type(device_id, detection_type)` — make tests pass
- [x] `get_enabled_detection_types(device_id)` — make tests pass

### 5. Sunrise/Sunset Calculation

**RED** — Write failing tests (`tests/test_solar_service.py`):
- [x] Test with known lat/long and date for predictable sunrise/sunset
- [x] Test offset handling (positive and negative)
- [x] Test fill_value="1" (daytime active) and fill_value="0" (nighttime active)
- [x] Test edge cases: midnight crossings, polar regions (if applicable)

**GREEN** — Implement (`src/remander/services/solar.py`):
- [x] `get_sunrise_sunset(latitude, longitude, date=None)` — make tests pass
- [x] `compute_dynamic_bitmask(sunrise, sunset, ...)` — make tests pass

### 6. Bitmask Service

**RED** — Write failing tests (`tests/test_bitmask_service.py`):
- [x] Test `create_hour_bitmask(name, subtype, ...)` — create static or dynamic bitmask
- [x] Test `get_hour_bitmask(id)` — fetch by ID
- [x] Test `list_hour_bitmasks()` — list all
- [x] Test `update_hour_bitmask(id, ...)` — update
- [x] Test `delete_hour_bitmask(id)` — delete
- [x] Test `create_zone_mask(name, mask_value)` — create (validate 4800-char string of 0s and 1s)
- [x] Test `get_zone_mask(id)` — fetch by ID
- [x] Test `list_zone_masks()` — list all
- [x] Test `update_zone_mask(id, ...)` — update
- [x] Test `delete_zone_mask(id)` — delete
- [x] Test `assign_bitmask(device_id, mode, detection_type, hour_bitmask_id, zone_mask_id)` — create or update assignment
- [x] Test `get_assignments_for_device(device_id, mode=None)` — list assignments for a device
- [x] Test `delete_assignment(id)` — remove an assignment
- [x] Test `resolve_hour_bitmask(hour_bitmask, date=None)` — return the 24-char value
- [x] Test `resolve_bitmasks_for_device(device_id, mode)` — return resolved bitmasks per detection type

**GREEN** — Implement (`src/remander/services/bitmask.py`):
- [x] **Hour Bitmask CRUD**: `create_hour_bitmask`, `get_hour_bitmask`, `list_hour_bitmasks`, `update_hour_bitmask`, `delete_hour_bitmask` — make tests pass
- [x] **Zone Mask CRUD**: `create_zone_mask`, `get_zone_mask`, `list_zone_masks`, `update_zone_mask`, `delete_zone_mask` — make tests pass
- [x] **Bitmask Assignment CRUD**: `assign_bitmask`, `get_assignments_for_device`, `delete_assignment` — make tests pass
- [x] **Bitmask Resolution**: `resolve_hour_bitmask`, `resolve_bitmasks_for_device` — make tests pass

### 7. Reolink NVR Client

**RED** — Write failing tests (`tests/test_reolink_client.py`, mocked — no real NVR needed):
- [x] Test `login()` — authenticate with the NVR
- [x] Test `logout()` — close the session
- [x] Test `list_channels()` — return list of connected cameras with metadata
- [x] Test `get_channel_info(channel)` — get detailed info for one camera
- [x] Test `get_alarm_schedule(channel, detection_type)` — get current notification bitmask
- [x] Test `set_alarm_schedule(channel, detection_type, hour_bitmask)` — set notification bitmask
- [x] Test `get_detection_zones(channel, detection_type)` — get current zone mask
- [x] Test `set_detection_zones(channel, detection_type, zone_mask)` — set zone mask
- [x] Test `move_to_preset(channel, preset_index, speed)` — PTZ move to preset
- [x] Test `is_channel_online(channel)` — check if a camera channel is online

**GREEN** — Implement (`src/remander/clients/reolink.py`):
- [x] `ReolinkNVRClient` class wrapping reolink-aio — make tests pass
- [x] Investigate reolink-aio API coverage vs. direct HTTP calls needed

### 8. Tapo Power Client

**RED** — Write failing tests (`tests/test_tapo_client.py`, mocked python-kasa):
- [x] Test `turn_on(ip_address)` — power on the plug
- [x] Test `turn_off(ip_address)` — power off the plug
- [x] Test `is_on(ip_address)` — check current power state

**GREEN** — Implement (`src/remander/clients/tapo.py`):
- [x] `TapoClient` class wrapping python-kasa — make tests pass

### 9. Sonoff Mini R2 Client

**RED** — Write failing tests (`tests/test_sonoff_client.py`, mocked httpx):
- [x] Test `turn_on(ip_address)` — POST to /zeroconf/switch with `{"data": {"switch": "on"}}`
- [x] Test `turn_off(ip_address)` — POST to /zeroconf/switch with `{"data": {"switch": "off"}}`
- [x] Test `is_on(ip_address)` — POST to /zeroconf/info, parse switch state from response

**GREEN** — Implement (`src/remander/clients/sonoff.py`):
- [x] `SonoffClient` class using httpx — make tests pass

### 10. Final Verification
- [x] All new tests pass (`make test`)
- [x] `make lint` passes with no errors
- [x] `make format` produces no changes
- [x] Device CRUD: create, read, update, delete cameras and power devices
- [x] Tag CRUD: create, list, delete tags; assign/remove from devices
- [x] Detection types: set, enable, disable per device
- [x] Bitmask CRUD: create static/dynamic hour bitmasks, zone masks, assignments
- [x] Dynamic bitmask: sunrise/sunset calculation produces correct 24-char values
- [x] Bitmask resolution: resolves correct values per device + mode + detection type
- [x] NVR client: all methods tested with mocked reolink-aio
- [x] Tapo client: on/off/status tested with mocked python-kasa
- [x] Sonoff client: on/off/status tested with mocked httpx

---

# Milestone 3: Command & Workflow Engine

**Goal**: The core intelligence — commands, workflows, scheduling, validation, notifications.

**Exit criteria**: All five command types execute correctly end-to-end (in tests). Commands queue
properly. Delayed and re-arm timers fire correctly. Notifications send. Activity log captures all
steps.

**Methodology**: Red/green TDD — write failing tests first, then implement to make them pass.

**Status**: Complete

---

## Tasks

### 1. SAQ Worker Integration

**RED** — Write failing tests (`tests/test_saq_worker.py`):
- [ ] Test SAQ queue is created with correct Redis URL from settings
- [ ] Test worker starts during FastAPI lifespan startup
- [ ] Test worker shuts down cleanly during FastAPI lifespan shutdown
- [ ] Test worker concurrency is set to 1 (one-command-at-a-time constraint)

**GREEN** — Implement:
- [ ] Add SAQ queue configuration to `src/remander/config.py` (Redis URL, concurrency)
- [ ] Create `src/remander/worker.py` — SAQ queue setup and job registration
- [ ] Integrate SAQ worker startup/shutdown into FastAPI lifespan in `src/remander/main.py`

### 2. Command Service

**RED** — Write failing tests (`tests/test_command_service.py`):
- [ ] Test `create_command(command_type, ...)` — create with initial `pending` status, records `initiated_by_ip` and optional `initiated_by_user`
- [ ] Test `create_command` with `tag_filter` (for Pause commands)
- [ ] Test `create_command` with `delay_minutes` (for Set Away Delayed)
- [ ] Test `create_command` with `pause_minutes` (for Pause commands)
- [ ] Test `get_command(id)` — fetch command with all fields
- [ ] Test `list_commands(status=None, limit=None)` — list/filter commands
- [ ] Test `transition_status(id, new_status)` — valid transitions (pending→queued→running→succeeded/failed/cancelled/completed_with_errors)
- [ ] Test `transition_status` rejects invalid transitions (e.g., succeeded→running)
- [ ] Test `transition_status` records timestamps (`queued_at`, `started_at`, `completed_at`)
- [ ] Test `cancel_command(id)` — cancel a pending or queued command
- [ ] Test `cancel_command` rejects cancelling a completed command
- [ ] Test `get_next_queued()` — returns oldest queued command (FIFO)
- [ ] Test `get_active_command()` — returns the currently running command, or None
- [ ] Test `set_error_summary(id, message)` — store error details on command

**GREEN** — Implement (`src/remander/services/command.py`):
- [ ] `create_command(command_type, ...)` — make tests pass
- [ ] `get_command(id)` — make tests pass
- [ ] `list_commands(status=None, limit=None)` — make tests pass
- [ ] `transition_status(id, new_status)` — make tests pass (enforce valid transitions, record timestamps)
- [ ] `cancel_command(id)` — make tests pass
- [ ] `get_next_queued()` — make tests pass
- [ ] `get_active_command()` — make tests pass
- [ ] `set_error_summary(id, message)` — make tests pass

### 3. Activity Logging Service

**RED** — Write failing tests (`tests/test_activity_service.py`):
- [ ] Test `log_activity(command_id, device_id, node_name, status, ...)` — create a log entry with `started` status
- [ ] Test `log_activity` with `detail` text and `duration_ms`
- [ ] Test `log_activity` with `device_id=None` (for non-device-specific steps like NVR login)
- [ ] Test `get_activities_for_command(command_id)` — list all log entries for a command, ordered by created_at
- [ ] Test `get_activities_for_device(device_id)` — list across commands
- [ ] Test `update_activity_status(id, status, duration_ms, detail)` — mark as succeeded/failed/skipped

**GREEN** — Implement (`src/remander/services/activity.py`):
- [ ] `log_activity(command_id, device_id, node_name, status, ...)` — make tests pass
- [ ] `get_activities_for_command(command_id)` — make tests pass
- [ ] `get_activities_for_device(device_id)` — make tests pass
- [ ] `update_activity_status(id, status, duration_ms, detail)` — make tests pass

### 4. Notification Sender

**RED** — Write failing tests (`tests/test_notification.py`):
- [ ] Test `NotificationSender` protocol is satisfied by `EmailNotificationSender`
- [ ] Test `EmailNotificationSender.send(subject, body)` — calls aiosmtplib with correct SMTP settings
- [ ] Test `EmailNotificationSender.send(subject, body, html_body=...)` — sends multipart email
- [ ] Test `render_command_succeeded_notification(command)` — returns subject and body
- [ ] Test `render_command_failed_notification(command, error)` — returns subject and body
- [ ] Test `render_completed_with_errors_notification(command, successes, failures)` — returns subject and body
- [ ] Test `render_validation_warnings_notification(command, discrepancies)` — returns subject and body

**GREEN** — Implement:
- [ ] Create `src/remander/services/notification.py` — `NotificationSender` Protocol class
- [ ] Create `src/remander/clients/email.py` — `EmailNotificationSender` attrs class using aiosmtplib
- [ ] Create `src/remander/services/notification_templates.py` — 4 render functions for notification content

### 5. Workflow State & Context

**RED** — Write failing tests (`tests/test_workflow_state.py`):
- [ ] Test `WorkflowState` creation with command, device list, and settings
- [ ] Test `WorkflowState` tracks per-device results (success/failure/skipped)
- [ ] Test `WorkflowState` records whether the overall workflow has errors
- [ ] Test `WorkflowState` holds references to NVR client, notification sender

**GREEN** — Implement (`src/remander/workflows/state.py`):
- [ ] Create `WorkflowState` Pydantic model — shared state passed through all workflow nodes
- [ ] Include: command reference, device list, NVR client, per-device results, error tracking

### 6. Workflow Nodes — Infrastructure

**RED** — Write failing tests (`tests/test_workflow_nodes.py`):
- [ ] Test `NVRLoginNode` — calls `reolink_client.login()`, logs activity
- [ ] Test `NVRLoginNode` — handles login failure (logs error, sets workflow error state)
- [ ] Test `NVRLogoutNode` — calls `reolink_client.logout()`, logs activity
- [ ] Test `OptionalDelayNode` — waits for `delay_minutes` when set
- [ ] Test `OptionalDelayNode` — skips when `delay_minutes` is None or 0
- [ ] Test `FilterByTagNode` — filters device list to only devices matching tag_filter
- [ ] Test `FilterByTagNode` — passes through all devices when tag_filter is None
- [ ] Test `NotifyNode` — calls `notification_sender.send()` with rendered template
- [ ] Test `NotifyNode` — handles send failure gracefully (logs error, doesn't fail workflow)
- [ ] Test `ValidateNode` — compares NVR actual bitmasks to expected values
- [ ] Test `ValidateNode` — logs discrepancies as activity entries with `failed` status
- [ ] Test `ValidateNode` — passes when all bitmasks match

**GREEN** — Implement (`src/remander/workflows/nodes/`):
- [ ] Create `src/remander/workflows/nodes/__init__.py`
- [ ] Create `src/remander/workflows/nodes/nvr.py` — `NVRLoginNode`, `NVRLogoutNode`
- [ ] Create `src/remander/workflows/nodes/delay.py` — `OptionalDelayNode`
- [ ] Create `src/remander/workflows/nodes/filter.py` — `FilterByTagNode`
- [ ] Create `src/remander/workflows/nodes/notify.py` — `NotifyNode`
- [ ] Create `src/remander/workflows/nodes/validate.py` — `ValidateNode`

### 7. Workflow Nodes — Device Operations

**RED** — Write failing tests (`tests/test_workflow_device_nodes.py`):
- [ ] Test `SaveBitmasksNode` — reads current bitmasks from NVR and saves to `saved_device_state`
- [ ] Test `RestoreBitmasksNode` — reads from `saved_device_state` and writes back to NVR
- [ ] Test `PowerOnNode` — sends power-on to each camera's associated power device (Tapo/Sonoff)
- [ ] Test `PowerOnNode` — skips cameras without power devices
- [ ] Test `WaitForPowerOnNode` — polls NVR until cameras come online (mocked polling)
- [ ] Test `WaitForPowerOnNode` — times out after 120s with error logged per camera
- [ ] Test `PowerOffNode` — sends power-off to power devices
- [ ] Test `PTZCalibrateNode` — runs PTZ calibration sequence on PTZ cameras
- [ ] Test `SetPTZPresetNode` — moves cameras to away-mode preset
- [ ] Test `SetPTZHomeNode` — moves cameras to home-mode preset
- [ ] Test `SetNotificationBitmasksNode` — applies resolved hour bitmasks via NVR client
- [ ] Test `SetNotificationBitmasksNode` — handles per-device failure (continues to next device)
- [ ] Test `SetZoneMasksNode` — applies zone masks via NVR client
- [ ] Test `SetZoneMasksNode` — handles per-device failure (continues to next device)

**GREEN** — Implement (`src/remander/workflows/nodes/`):
- [ ] Create `src/remander/workflows/nodes/save_restore.py` — `SaveBitmasksNode`, `RestoreBitmasksNode`
- [ ] Create `src/remander/workflows/nodes/power.py` — `PowerOnNode`, `WaitForPowerOnNode`, `PowerOffNode`
- [ ] Create `src/remander/workflows/nodes/ptz.py` — `PTZCalibrateNode`, `SetPTZPresetNode`, `SetPTZHomeNode`
- [ ] Create `src/remander/workflows/nodes/bitmask.py` — `SetNotificationBitmasksNode`, `SetZoneMasksNode`

### 8. Workflow Graph Definitions

**RED** — Write failing tests (`tests/test_workflows.py`):
- [ ] Test `SetAwayWorkflow` — runs all nodes in correct order with mocked clients
- [ ] Test `SetAwayWorkflow` — handles partial failure (some cameras fail, others succeed)
- [ ] Test `SetAwayWorkflow` — produces `completed_with_errors` on partial failure
- [ ] Test `SetAwayDelayedWorkflow` — includes delay node before Set Away logic
- [ ] Test `SetHomeWorkflow` — runs restore, PTZ home, power off in correct order
- [ ] Test `PauseNotificationsWorkflow` — filters by tag, saves bitmasks, zeros them out, schedules re-arm
- [ ] Test `PauseRecordingWorkflow` — filters by tag, saves bitmasks, zeros them out, schedules re-arm
- [ ] Test `ReArmWorkflow` — restores saved bitmasks, validates, notifies

**GREEN** — Implement (`src/remander/workflows/`):
- [ ] Create `src/remander/workflows/set_away.py` — `SetAwayGraph` pydantic-graph definition
- [ ] Create `src/remander/workflows/set_home.py` — `SetHomeGraph` pydantic-graph definition
- [ ] Create `src/remander/workflows/pause_notifications.py` — `PauseNotificationsGraph` pydantic-graph definition
- [ ] Create `src/remander/workflows/pause_recording.py` — `PauseRecordingGraph` pydantic-graph definition
- [ ] Create `src/remander/workflows/rearm.py` — `ReArmGraph` pydantic-graph definition
- [ ] Create `src/remander/workflows/__init__.py` — register all workflows, map CommandType → Graph

### 9. Command Queueing & Execution

**RED** — Write failing tests (`tests/test_command_queue.py`):
- [x] Test `enqueue_command(command_id)` — transitions to queued, enqueues SAQ job
- [x] Test `process_command(command_id)` — picks up command, transitions running→succeeded
- [x] Test FIFO ordering — commands execute in creation order
- [x] Test one-at-a-time — second command waits while first is running
- [x] Test command cancellation — cancelled command is skipped, next command runs
- [x] Test `process_command` handles workflow failure — transitions to failed, records error

**GREEN** — Implement:
- [x] Create `src/remander/services/queue.py` — `enqueue_command`, `execute_command` (SAQ job handler)
- [x] Wire `process_command` in worker.py to call `execute_command`

### 10. Delayed Commands & Re-arm Scheduling

**RED** — Write failing tests (`tests/test_scheduling.py`):
- [x] Test `schedule_delayed_command(command_id, delay_minutes)` — creates SAQ job with correct delay
- [x] Test delayed job stores job ID on command
- [x] Test `cancel_delayed_command(command_id)` — cancels the SAQ job and clears job ID
- [x] Test cancel is a no-op when no job ID exists
- [x] Test `schedule_rearm(command_id, pause_minutes)` — creates SAQ timer job
- [x] Test re-arm stores job ID on command
- [x] Test `cancel_pending_rearms()` — cancels all rearm jobs for pause commands
- [x] Test `cancel_pending_rearms()` clears job IDs
- [x] Test `cancel_pending_rearms()` ignores non-pause commands
- [x] Test `cancel_pending_rearms()` ignores commands without job IDs

**GREEN** — Implement (`src/remander/services/scheduling.py`):
- [x] `schedule_delayed_command(command_id, delay_minutes)` — make tests pass
- [x] `cancel_delayed_command(command_id)` — make tests pass
- [x] `schedule_rearm(command_id, pause_minutes)` — make tests pass
- [x] `cancel_pending_rearms()` — cancel all pending re-arm timers (called by Set Home/Set Away)
- [x] Wire `ScheduleReArmNode` to call `schedule_rearm`
- [x] Add `process_rearm` SAQ job handler + `execute_rearm` in queue service

### 11. Validation Service

**RED** — Write failing tests (`tests/test_validation_service.py`):
- [x] Test `validate_device_bitmasks(device, expected)` — queries NVR, compares values
- [x] Test validation passes when all values match
- [x] Test validation detects hour bitmask mismatch — returns discrepancy details
- [x] Test validation detects zone mask mismatch — returns discrepancy details
- [x] Test validation detects multiple mismatches
- [x] Test validation skips device without channel
- [x] Test `validate_command_results` logs discrepancies to activity log
- [x] Test validation does not change command status (discrepancies are warnings only)

**GREEN** — Implement (`src/remander/services/validation.py`):
- [x] `validate_device_bitmasks(device, expected, nvr_client)` — make tests pass
- [x] `validate_command_results(command_id, expected_bitmasks, nvr_client)` — orchestrate per-device validation

### 12. Final Verification
- [x] All new tests pass (`make test`) — 244 tests passing
- [x] `make lint` passes with no errors
- [x] `make format` produces no changes
- [x] Command creation: all 5 types with correct fields
- [x] Command lifecycle: full state machine (pending→queued→running→terminal)
- [x] FIFO queue: commands execute one-at-a-time in order
- [x] Set Away workflow: full end-to-end with mocked hardware
- [x] Set Away Delayed workflow: delay fires, then Set Away executes
- [x] Set Home workflow: restore bitmasks, PTZ home, power off
- [x] Pause Notifications workflow: filter, save, zero out, schedule re-arm
- [x] Pause Recording workflow: filter, save, zero out, schedule re-arm
- [x] Re-Arm workflow: restore saved bitmasks, validate
- [x] Delayed commands: SAQ job fires after delay
- [x] Re-arm timers: SAQ timer fires and runs Re-Arm; cancelled by Set Home/Set Away
- [x] Validation: post-command NVR verification detects mismatches as warnings
- [x] Notifications: email sends for succeeded, failed, completed_with_errors, validation warnings
- [x] Activity logging: every node execution logged per-device with status and duration
