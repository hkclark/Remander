# Remander — Project Specification

> **Version**: 1.0 (2026-03-03)
> **Status**: Draft

---

## Table of Contents

1. [Overview](#1-overview)
2. [Glossary](#2-glossary)
3. [Architecture Overview](#3-architecture-overview)
4. [Technology Stack](#4-technology-stack)
5. [Configuration](#5-configuration)
6. [Data Model](#6-data-model)
7. [Devices](#7-devices)
8. [Bitmasks](#8-bitmasks)
9. [Commands](#9-commands)
10. [Workflows (Pydantic AI Graphs)](#10-workflows-pydantic-ai-graphs)
11. [Job Scheduling (SAQ + Redis)](#11-job-scheduling-saq--redis)
12. [Notification System](#12-notification-system)
13. [Activity Log & Audit Trail](#13-activity-log--audit-trail)
14. [Validation](#14-validation)
15. [Web UI](#15-web-ui)
16. [Hardware Integration](#16-hardware-integration)
17. [Docker & Deployment](#17-docker--deployment)
18. [Development Workflow](#18-development-workflow)
19. [Future Considerations](#19-future-considerations)
20. [Milestones](#20-milestones)

---

## 1. Overview

Remander is a home automation application that configures **Reolink security cameras** for different
behavior depending on whether the user is **at home** or **away from home**.

- **Away mode**: cameras are fully armed — all notification bitmasks active, detection zones set,
  PTZ cameras moved to monitoring presets, powered-off cameras turned on.
- **Home mode**: cameras are partially or fully disarmed — notification bitmasks zeroed or reduced,
  PTZ cameras returned to a neutral position, selected cameras powered off.

The application talks to a **single Reolink NVR** (Network Video Recorder) to configure all cameras
centrally. It also controls **non-Reolink power devices** (Tapo smart plugs, Sonoff Mini R2 switches)
that supply power to cameras that are physically turned off when the user is home.

All operations are executed as **commands** — auditable, queueable units of work that flow through
**workflow graphs** built with Pydantic AI's `pydantic-graph`.

---

## 2. Glossary

| Term | Definition |
|---|---|
| **Device** | Any hardware entity managed by Remander: a camera or a power-control device. |
| **Channel** | The NVR channel number assigned to a camera (0-indexed). |
| **Hour Bitmask** | A 24-character string where each character (`0` or `1`) represents one hour of the day. Used by Reolink to schedule when alerts/recording are active. |
| **Zone Mask** | An 80x60 grid (4,800 characters of `0`s and `1`s) defining which spatial zones trigger motion detection on a camera. |
| **Detection Type** | A category of motion detection supported by a camera: `motion`, `person`, `vehicle`, `animal`, `face`, `package`. |
| **Command** | A user-initiated operation (e.g., "Set Away Now") that progresses through a state machine and executes a workflow. |
| **Workflow** | A directed graph of steps (nodes) executed by the Pydantic AI graph engine to carry out a command. |
| **Tag** | A user-defined label applied to devices for grouping and filtering (e.g., "front-yard", "indoor"). |
| **Mode** | The current system state: `home` or `away`. |
| **NVR** | Reolink Network Video Recorder — the central hub through which all camera configuration is performed. |

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Remander App Container                │  │
│  │                                                    │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────────┐  │  │
│  │  │ FastAPI   │   │ SAQ      │   │ Pydantic AI  │  │  │
│  │  │ (Web UI)  │   │ Worker   │   │ (Workflows)  │  │  │
│  │  │ + HTMX    │   │          │   │              │  │  │
│  │  └────┬─────┘   └────┬─────┘   └──────┬───────┘  │  │
│  │       │              │                 │          │  │
│  │       └──────┬───────┴─────────────────┘          │  │
│  │              │                                    │  │
│  │       ┌──────┴──────┐                             │  │
│  │       │ Tortoise ORM│                             │  │
│  │       └──────┬──────┘                             │  │
│  │              │                                    │  │
│  │       ┌──────┴──────┐                             │  │
│  │       │   SQLite DB  │                            │  │
│  │       └─────────────┘                             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────┐                                      │
│  │  Redis Container│                                     │
│  └────────┬───────┘                                      │
│           │ (SAQ job queue)                               │
└───────────┼──────────────────────────────────────────────┘
            │
     ┌──────┴──────────────────────────────────┐
     │            Local Network                 │
     │                                          │
     │  ┌──────────┐  ┌───────┐  ┌──────────┐ │
     │  │ Reolink  │  │ Tapo  │  │ Sonoff   │ │
     │  │ NVR      │  │ Plugs │  │ Mini R2  │ │
     │  └──────────┘  └───────┘  └──────────┘ │
     └──────────────────────────────────────────┘
```

**Key flows:**

1. **User action** (browser) -> FastAPI -> creates a `command` row -> enqueues SAQ job
2. **SAQ worker** picks up job -> instantiates pydantic-graph workflow -> executes nodes
3. **Workflow nodes** call hardware clients (reolink-aio, python-kasa, HTTP) and write to the database
4. **Completion** -> notification sent (email) -> activity log finalized

---

## 4. Technology Stack

| Category | Library / Tool | Purpose |
|---|---|---|
| Language | Python 3.14 | Runtime |
| Web framework | FastAPI | HTTP routing, API, SSR |
| Templating | Jinja2 | Server-side HTML rendering |
| Frontend interactivity | HTMX | Hypermedia-driven UI updates |
| CSS | Tailwind CSS | Utility-first styling |
| ORM | Tortoise ORM | Async ORM for SQLite/PostgreSQL |
| Database | SQLite | Primary data store (PostgreSQL-ready) |
| Migrations | Aerich | Tortoise ORM migration tool |
| Workflow engine | Pydantic AI (`pydantic-graph`) | Directed-graph workflow execution |
| Job queue | SAQ | Async job queue built on Redis |
| Queue backend | Redis | Job queue and scheduling backend |
| Validation / config | Pydantic + pydantic-settings | Settings, API models, workflow state |
| Domain classes | attrs | Domain objects, value objects, utility classes |
| Reolink integration | reolink-aio | Async Reolink NVR/camera API client |
| Tapo integration | python-kasa | Async TP-Link Kasa/Tapo device control |
| Sonoff integration | httpx | Direct HTTP API calls to Sonoff Mini R2 |
| Sunrise/sunset | astral | Solar time calculation for dynamic bitmasks |
| Email | aiosmtplib | Async SMTP email sending |
| Linter / formatter | Ruff | Linting (replaces flake8) + Black-compatible formatting |
| Package manager | uv | Fast Python package management |
| Testing | pytest + pytest-asyncio | Async test execution |
| Containerization | Docker + Docker Compose | Deployment |

---

## 5. Configuration

All configuration is managed via **pydantic-settings**, loaded from environment variables and/or a
`.env` file.

### Settings Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `NVR_HOST` | `str` | *(required)* | Reolink NVR IP address or hostname |
| `NVR_PORT` | `int` | `443` | Reolink NVR HTTPS port |
| `NVR_USERNAME` | `str` | *(required)* | NVR login username |
| `NVR_PASSWORD` | `SecretStr` | *(required)* | NVR login password |
| `REDIS_URL` | `str` | `redis://redis:6379/0` | Redis connection URL for SAQ |
| `DATABASE_URL` | `str` | `sqlite:///data/remander.db` | Tortoise ORM database URL |
| `SMTP_HOST` | `str` | `""` | SMTP server hostname |
| `SMTP_PORT` | `int` | `587` | SMTP server port |
| `SMTP_USERNAME` | `str` | `""` | SMTP login username |
| `SMTP_PASSWORD` | `SecretStr` | `""` | SMTP login password |
| `SMTP_FROM` | `str` | `""` | From address for notification emails |
| `SMTP_TO` | `str` | `""` | Recipient address for notification emails |
| `SMTP_USE_TLS` | `bool` | `True` | Use STARTTLS for SMTP |
| `LATITUDE` | `float` | `0.0` | Location latitude for sunrise/sunset calculation |
| `LONGITUDE` | `float` | `0.0` | Location longitude for sunrise/sunset calculation |
| `LOG_DIR` | `str` | `./logs` | Directory for log file output |
| `LOG_LEVEL` | `str` | `INFO` | Logging level |
| `PUID` | `int` | `1000` | User ID for file ownership in Docker |
| `PGID` | `int` | `1000` | Group ID for file ownership in Docker |
| `POWER_ON_TIMEOUT_SECONDS` | `int` | `120` | Max wait time for powered-on cameras to come online |
| `POWER_ON_POLL_INTERVAL_SECONDS` | `int` | `10` | Polling interval when waiting for cameras |

### .env.example

```env
# Reolink NVR
NVR_HOST=192.168.1.100
NVR_PORT=443
NVR_USERNAME=admin
NVR_PASSWORD=changeme

# Redis (SAQ job queue)
REDIS_URL=redis://redis:6379/0

# Database
DATABASE_URL=sqlite:///data/remander.db

# Email Notifications
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=changeme
SMTP_FROM=alerts@example.com
SMTP_TO=you@example.com
SMTP_USE_TLS=true

# Location (for sunrise/sunset calculation)
LATITUDE=40.7128
LONGITUDE=-74.0060

# Logging
LOG_DIR=./logs
LOG_LEVEL=INFO

# Docker user/group
PUID=1000
PGID=1000

# Power-on timing
POWER_ON_TIMEOUT_SECONDS=120
POWER_ON_POLL_INTERVAL_SECONDS=10
```

---

## 6. Data Model

All models use **Tortoise ORM**. Enums are Python `StrEnum` types.

### Enums

```python
class DeviceType(StrEnum):
    CAMERA = "camera"
    POWER = "power"

class DeviceBrand(StrEnum):
    REOLINK = "reolink"
    TAPO = "tapo"
    SONOFF = "sonoff"

class PowerDeviceSubtype(StrEnum):
    SMART_PLUG = "smart_plug"
    INLINE_SWITCH = "inline_switch"

class DetectionType(StrEnum):
    MOTION = "motion"
    PERSON = "person"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    FACE = "face"
    PACKAGE = "package"

class HourBitmaskSubtype(StrEnum):
    STATIC = "static"
    DYNAMIC = "dynamic"

class Mode(StrEnum):
    HOME = "home"
    AWAY = "away"

class CommandType(StrEnum):
    SET_AWAY_NOW = "set_away_now"
    SET_AWAY_DELAYED = "set_away_delayed"
    SET_HOME_NOW = "set_home_now"
    PAUSE_NOTIFICATIONS = "pause_notifications"
    PAUSE_RECORDING = "pause_recording"

class CommandStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED_WITH_ERRORS = "completed_with_errors"

class ActivityStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### Tables

#### `device`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `name` | `str` | unique, not null | Human-readable device name |
| `device_type` | `DeviceType` | not null | `camera` or `power` |
| `device_subtype` | `str` | nullable | Subtype (e.g., `smart_plug`, `inline_switch` for power devices) |
| `brand` | `DeviceBrand` | not null | `reolink`, `tapo`, or `sonoff` |
| `model` | `str` | nullable | Device model number |
| `hw_version` | `str` | nullable | Hardware version |
| `firmware` | `str` | nullable | Firmware version |
| `ip_address` | `str` | nullable | Device IP address on local network |
| `channel` | `int` | nullable | NVR channel number (cameras only, 0-indexed) |
| `is_wireless` | `bool` | default `False` | Whether the camera connects wirelessly |
| `is_poe` | `bool` | default `False` | Whether the camera uses Power over Ethernet |
| `resolution` | `str` | nullable | Camera resolution (e.g., `2560x1440`) |
| `has_ptz` | `bool` | default `False` | Whether the camera supports PTZ |
| `ptz_away_preset` | `int` | nullable | PTZ preset index for away mode |
| `ptz_home_preset` | `int` | nullable | PTZ preset index for home mode |
| `ptz_speed` | `int` | nullable | PTZ movement speed |
| `power_device_id` | `int` | FK -> `device.id`, nullable | Power device that controls this camera's power |
| `notes` | `str` | nullable | Free-text notes |
| `is_enabled` | `bool` | default `True` | Whether this device participates in commands |
| `created_at` | `datetime` | auto | Row creation timestamp |
| `updated_at` | `datetime` | auto | Row update timestamp |

#### `tag`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `name` | `str` | unique, not null | Tag name (e.g., "front-yard", "indoor") |

#### `device_tag`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `device_id` | `int` | FK -> `device.id`, not null | Device reference |
| `tag_id` | `int` | FK -> `tag.id`, not null | Tag reference |

Unique constraint on `(device_id, tag_id)`.

#### `hour_bitmask`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `name` | `str` | unique, not null | Human-readable name (e.g., "Nighttime Only") |
| `subtype` | `HourBitmaskSubtype` | not null | `static` or `dynamic` |
| `static_value` | `str` | nullable | 24-char bitmask for static subtype |
| `sunrise_offset_minutes` | `int` | nullable | Minutes to add/subtract from sunrise (dynamic only) |
| `sunset_offset_minutes` | `int` | nullable | Minutes to add/subtract from sunset (dynamic only) |
| `fill_value` | `str` | nullable, `"0"` or `"1"` | Value used to fill hours between sunrise and sunset (dynamic only) |
| `created_at` | `datetime` | auto | Row creation timestamp |
| `updated_at` | `datetime` | auto | Row update timestamp |

#### `zone_mask`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `name` | `str` | unique, not null | Human-readable name (e.g., "Full Frame", "Lower Half") |
| `mask_value` | `str` | not null | 4,800-character string of `0`s and `1`s (80 columns x 60 rows) |
| `created_at` | `datetime` | auto | Row creation timestamp |
| `updated_at` | `datetime` | auto | Row update timestamp |

#### `device_detection_type`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `device_id` | `int` | FK -> `device.id`, not null | Device reference |
| `detection_type` | `DetectionType` | not null | Type of detection |
| `is_enabled` | `bool` | default `True` | Whether this detection type is active for this device |

Unique constraint on `(device_id, detection_type)`.

#### `device_bitmask_assignment`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `device_id` | `int` | FK -> `device.id`, not null | Device reference |
| `mode` | `Mode` | not null | `home` or `away` |
| `detection_type` | `DetectionType` | not null | Which detection type this assignment covers |
| `hour_bitmask_id` | `int` | FK -> `hour_bitmask.id`, nullable | Hour bitmask to apply (null = all zeros) |
| `zone_mask_id` | `int` | FK -> `zone_mask.id`, nullable | Zone mask to apply (null = no change) |

Unique constraint on `(device_id, mode, detection_type)`.

#### `command`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `command_type` | `CommandType` | not null | Type of command |
| `status` | `CommandStatus` | not null, default `pending` | Current status |
| `delay_minutes` | `int` | nullable | Delay before execution (for `set_away_delayed`) |
| `pause_minutes` | `int` | nullable | Duration of pause (for pause commands) |
| `tag_filter` | `str` | nullable | Comma-separated tag names to filter devices |
| `initiated_by_ip` | `str` | nullable | IP address of the requester |
| `initiated_by_user` | `str` | nullable | Username of the requester (from `?user=` param) |
| `saq_job_id` | `str` | nullable | SAQ job ID for tracking/cancellation |
| `error_summary` | `str` | nullable | Summary of errors if status is `failed` or `completed_with_errors` |
| `created_at` | `datetime` | auto | When the command was created |
| `queued_at` | `datetime` | nullable | When the command entered the queue |
| `started_at` | `datetime` | nullable | When execution began |
| `completed_at` | `datetime` | nullable | When execution finished |

#### `activity_log`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `command_id` | `int` | FK -> `command.id`, not null | Parent command |
| `device_id` | `int` | FK -> `device.id`, nullable | Device involved (null for command-level entries) |
| `step_name` | `str` | not null | Name of the workflow step (e.g., `nvr_login`, `set_bitmask`) |
| `status` | `ActivityStatus` | not null | Step outcome |
| `detail` | `str` | nullable | Additional detail or error message |
| `duration_ms` | `int` | nullable | Step execution time in milliseconds |
| `created_at` | `datetime` | auto | When the log entry was created |

#### `saved_device_state`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `int` | PK, auto | Primary key |
| `command_id` | `int` | FK -> `command.id`, not null | Command that saved this state |
| `device_id` | `int` | FK -> `device.id`, not null | Device whose state was saved |
| `detection_type` | `DetectionType` | not null | Which detection type |
| `saved_hour_bitmask` | `str` | nullable | The hour bitmask value that was active before the command |
| `saved_zone_mask` | `str` | nullable | The zone mask value that was active before the command |
| `is_consumed` | `bool` | default `False` | Whether this state has been restored |
| `created_at` | `datetime` | auto | When the state was saved |

#### `app_state`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `key` | `str` | PK | State key |
| `value` | `str` | not null | State value |
| `updated_at` | `datetime` | auto | When this value was last changed |

**Well-known keys:**

| Key | Values | Description |
|---|---|---|
| `current_mode` | `home`, `away` | The current system mode |
| `active_command_id` | command ID or empty | The currently executing command |

---

## 7. Devices

### 7.1 Cameras

Cameras are Reolink devices connected to the NVR. Each camera is identified by its **channel**
number on the NVR.

**Camera metadata** (model, hardware version, firmware, resolution, wireless/PoE status) is stored
for reference and can be auto-populated by querying the NVR.

**PTZ cameras** have additional configuration:
- `ptz_away_preset`: The preset index the camera should move to when entering away mode.
- `ptz_home_preset`: The preset index the camera should return to when entering home mode.
- `ptz_speed`: Movement speed for PTZ operations.

**Detection types** are configured per camera. Each camera can support a subset of the available
detection types (`motion`, `person`, `vehicle`, `animal`, `face`, `package`). The
`device_detection_type` table tracks which types a camera supports and whether each is enabled.

### 7.2 Power Devices

Power devices control the electrical supply to cameras. Two types are supported:

- **Tapo smart plugs** — controlled via the `python-kasa` library (async, local network).
- **Sonoff Mini R2 inline switches** — controlled via direct HTTP API calls (local network).

Each power device has an IP address and can be commanded to turn on, turn off, or report status.

### 7.3 Camera-to-Power-Device Association

A camera may optionally reference a power device via `power_device_id`. When a command needs to
power on a camera:

1. The workflow sends a power-on command to the associated power device.
2. It polls the NVR (up to `POWER_ON_TIMEOUT_SECONDS`, every `POWER_ON_POLL_INTERVAL_SECONDS`)
   waiting for the camera's channel to come online.
3. Once online, the workflow proceeds with PTZ calibration and bitmask configuration.

When powering off (home mode), the workflow powers off the device after all NVR configuration
changes are complete.

### 7.4 Tags

Tags provide flexible grouping of devices. A device can have multiple tags, and a tag can be
applied to multiple devices (many-to-many via `device_tag`).

Tags are used for:
- Filtering which devices a **Pause Notifications** or **Pause Recording** command applies to.
- Organizing devices in the UI.
- Future: per-tag command policies.

---

## 8. Bitmasks

### 8.1 Hour Bitmask

An hour bitmask is a **24-character string** where each character represents one hour of the day
(index 0 = midnight, index 23 = 11 PM). A `1` means the detection/notification is active during
that hour; a `0` means it is inactive.

**Example:** `000000011111111111100000` — active from 7 AM to 6 PM.

Two subtypes exist:

#### Static Bitmask
A fixed 24-character value that does not change. Stored directly in `static_value`.

#### Dynamic Bitmask
Calculated at runtime based on **sunrise and sunset times** for the configured location
(`LATITUDE`/`LONGITUDE`) using the `astral` library.

Parameters:
- `sunrise_offset_minutes`: Added to the calculated sunrise time (can be negative).
- `sunset_offset_minutes`: Added to the calculated sunset time (can be negative).
- `fill_value`: `"1"` to mark hours between sunrise and sunset as active, `"0"` to mark them as
  inactive (inverse behavior for nighttime-only schedules).

The sunrise and sunset times are **rounded to the nearest hour** to produce a clean 24-character
bitmask.

### 8.2 Zone Mask

A zone mask is an **80x60 grid** represented as a **4,800-character string** of `0`s and `1`s. It
defines the spatial detection zones on a camera's field of view. A `1` means motion in that grid
cell triggers detection; a `0` means it is ignored.

Zone masks are defined once and can be shared across multiple device assignments.

### 8.3 Bitmask Assignment

The `device_bitmask_assignment` table links a device + mode + detection type to a specific hour
bitmask and/or zone mask. This determines what configuration is applied to each camera when
entering a given mode.

**Calculation logic** when applying bitmasks during a command:

1. For each enabled camera, iterate over its enabled detection types.
2. Look up the `device_bitmask_assignment` for that device + current command's target mode +
   detection type.
3. If an assignment exists:
   - Resolve the hour bitmask value (static: use `static_value`; dynamic: calculate from
     sunrise/sunset).
   - Use the zone mask's `mask_value` if present.
4. If no assignment exists, or the detection type is disabled for the device, use **all-zeros**
   (24 zeros for hour bitmask, 4,800 zeros for zone mask).
5. Send the resolved values to the NVR via the Reolink API.

---

## 9. Commands

### 9.1 Command Types

| Command | Description |
|---|---|
| **Set Away Now** | Immediately transition all enabled cameras to away mode. |
| **Set Away Delayed** | Wait `delay_minutes`, then transition to away mode. |
| **Set Home Now** | Immediately transition all enabled cameras to home mode. |
| **Pause Notifications** | Temporarily zero out notification bitmasks for devices matching an optional tag filter. Automatically re-arms after `pause_minutes`. |
| **Pause Recording** | Temporarily zero out recording schedule bitmasks for devices matching an optional tag filter. Automatically re-arms after `pause_minutes`. |

### 9.2 Command Lifecycle

```
   ┌─────────┐
   │ pending  │  (created, awaiting queue processing)
   └────┬─────┘
        │
   ┌────▼─────┐
   │ queued    │  (in FIFO queue, waiting for active slot)
   └────┬─────┘
        │
   ┌────▼─────┐
   │ running   │  (workflow is executing)
   └────┬─────┘
        │
   ┌────▼──────────────────────────────────────────────┐
   │  succeeded │ failed │ cancelled │ completed_with_errors │
   └───────────────────────────────────────────────────┘
```

- **pending**: Command created, not yet enqueued. Used briefly during creation.
- **queued**: Command is in the FIFO queue waiting for the active slot.
- **running**: The SAQ worker is executing the command's workflow.
- **succeeded**: All workflow steps completed without error.
- **failed**: A critical/unrecoverable error occurred.
- **cancelled**: The command was cancelled before or during execution.
- **completed_with_errors**: The workflow finished but some devices had errors. Successful device
  configurations are **not rolled back**.

### 9.3 Command Queueing

Only **one command executes at a time**. Additional commands are placed in a **FIFO queue**. When
the active command completes, the next queued command begins.

> **Future enhancement**: An interruptibility matrix will allow high-priority commands (e.g.,
> "Set Away Now") to interrupt lower-priority running commands (e.g., "Pause Notifications").

### 9.4 Audit Trail

Every command records:
- `initiated_by_ip`: The IP address of the HTTP request that created the command.
- `initiated_by_user`: An optional username, provided via the `?user=` query parameter on the
  request URL.
- `created_at`, `queued_at`, `started_at`, `completed_at`: Timestamps for each lifecycle stage.

---

## 10. Workflows (Pydantic AI Graphs)

Each command type maps to a **pydantic-graph `Graph`**. Workflows are composed of **reusable
nodes** — small, focused units of work that can be shared across workflow definitions.

### 10.1 Reusable Node Library

| Node | Description |
|---|---|
| `OptionalDelayNode` | Waits for `delay_minutes` if set (used by Set Away Delayed). |
| `NVRLoginNode` | Authenticates with the Reolink NVR via reolink-aio. |
| `NVRLogoutNode` | Closes the NVR session. |
| `SaveBitmasksNode` | Reads current bitmask values from NVR and saves them to `saved_device_state`. |
| `RestoreBitmasksNode` | Reads saved state from `saved_device_state` and writes it back to the NVR. |
| `PowerOnNode` | Sends power-on commands to power devices for cameras that need to come online. |
| `WaitForPowerOnNode` | Polls NVR until powered-on cameras appear online (120s max, 10s interval). |
| `PowerOffNode` | Sends power-off commands to power devices. |
| `PTZCalibrateNode` | Runs PTZ calibration sequence on cameras that support it. |
| `SetPTZPresetNode` | Moves PTZ cameras to their away-mode preset position. |
| `SetPTZHomeNode` | Moves PTZ cameras to their home-mode preset position. |
| `SetNotificationBitmasksNode` | Applies resolved hour bitmasks to each camera's notification schedule. |
| `SetZoneMasksNode` | Applies zone masks to each camera's detection zones. |
| `FilterByTagNode` | Filters the device list to only those matching the command's tag filter. |
| `ScheduleReArmNode` | Enqueues a SAQ job to re-arm (restore bitmasks) after `pause_minutes`. |
| `ValidateNode` | Queries the NVR to verify bitmasks match expected values. |
| `NotifyNode` | Sends a notification (email) with the command result. |

### 10.2 Workflow Definitions

#### Set Away (Now & Delayed)

```
OptionalDelayNode (skip if Set Away Now)
    │
    ▼
NVRLoginNode
    │
    ▼
SaveBitmasksNode
    │
    ▼
PowerOnNode
    │
    ▼
WaitForPowerOnNode (120s max, 10s poll)
    │
    ▼
PTZCalibrateNode
    │
    ▼
SetPTZPresetNode (away presets)
    │
    ▼
SetNotificationBitmasksNode (away bitmasks)
    │
    ▼
SetZoneMasksNode (away zone masks)
    │
    ▼
ValidateNode
    │
    ▼
NVRLogoutNode
    │
    ▼
NotifyNode
```

#### Set Home

```
NVRLoginNode
    │
    ▼
RestoreBitmasksNode (restore to home-mode values)
    │
    ▼
SetPTZHomeNode
    │
    ▼
PowerOffNode (turn off cameras that should be off at home)
    │
    ▼
ValidateNode
    │
    ▼
NVRLogoutNode
    │
    ▼
NotifyNode
```

#### Pause Notifications

```
FilterByTagNode
    │
    ▼
NVRLoginNode
    │
    ▼
SaveBitmasksNode (save current notification bitmasks)
    │
    ▼
SetNotificationBitmasksNode (set all zeros)
    │
    ▼
NVRLogoutNode
    │
    ▼
ScheduleReArmNode (SAQ timer for pause_minutes)
```

#### Pause Recording

```
FilterByTagNode
    │
    ▼
NVRLoginNode
    │
    ▼
SaveBitmasksNode (save current recording bitmasks)
    │
    ▼
SetRecordingBitmasksNode (set all zeros)
    │
    ▼
NVRLogoutNode
    │
    ▼
ScheduleReArmNode (SAQ timer for pause_minutes)
```

#### Re-Arm (triggered by SAQ timer)

```
NVRLoginNode
    │
    ▼
RestoreBitmasksNode (restore saved bitmasks)
    │
    ▼
ValidateNode
    │
    ▼
NVRLogoutNode
    │
    ▼
NotifyNode
```

### 10.3 Error Handling

- **Per-node retry**: Each node may implement its own retry logic (e.g., NVR login retries on
  timeout).
- **Partial failure**: If a node fails for one device but succeeds for others, the workflow
  continues. The command's final status becomes `completed_with_errors`.
- **No rollback**: Successfully configured devices are **not** rolled back if other devices fail.
  The rationale is that a partially-armed system is better than a fully-unarmed one.
- **Activity logging**: Every node execution (success or failure) is recorded in `activity_log`.

---

## 11. Job Scheduling (SAQ + Redis)

### 11.1 Job Types

| Job | Trigger | Description |
|---|---|---|
| `process_command` | Command creation | Picks up the next queued command and runs its workflow. |
| `delayed_command` | Set Away Delayed | Fires after `delay_minutes` to start the Set Away workflow. |
| `rearm_timer` | Pause commands | Fires after `pause_minutes` to run the Re-Arm workflow. |

### 11.2 Worker Configuration

The SAQ worker runs **in-process** with the FastAPI application, started during the FastAPI
lifespan. Configuration:

- **Single worker** with configurable concurrency (default: 1 concurrent job, matching the
  one-command-at-a-time constraint).
- Jobs are durable in Redis — if the app restarts, pending jobs resume.

### 11.3 Job Cancellation

- **Re-arm timer jobs**: Cancelled if a full Set Home or Set Away command runs before the timer
  fires, since the full command will reconfigure all bitmasks and the saved state is no longer
  relevant.
- **Delayed command jobs**: Can be cancelled by the user from the UI before execution begins.

---

## 12. Notification System

### 12.1 Interface

```python
# Reason: protocol class — attrs not needed for abstract interface definition
class NotificationSender(Protocol):
    async def send(
        self,
        subject: str,
        body: str,
        *,
        html_body: str | None = None,
    ) -> None: ...
```

### 12.2 Email Implementation

The first (and initially only) implementation uses **aiosmtplib** to send email notifications via
SMTP. Configuration is read from the app settings (`SMTP_*` parameters).

### 12.3 Notification Templates

| Template | When Sent | Content |
|---|---|---|
| Command Succeeded | Command finishes with `succeeded` status | Summary of what was configured, device count, duration. |
| Command Failed | Command finishes with `failed` status | Error summary, which step failed, affected devices. |
| Completed with Errors | Command finishes with `completed_with_errors` | Summary of successes and failures per device. |
| Validation Warnings | Post-command validation finds discrepancies | List of devices where actual bitmasks don't match expected. |

### 12.4 Future Providers

The pluggable interface supports future additions:
- Pushover notifications
- Webhooks (generic HTTP POST)
- Other push notification services

---

## 13. Activity Log & Audit Trail

### 13.1 Activity Log

The `activity_log` table provides a granular record of every workflow step:

- **Per-device, per-step**: Each node execution for each device produces a log entry.
- **Status tracking**: `started`, `succeeded`, `failed`, `skipped`.
- **Duration**: Millisecond-precision timing for each step.
- **Detail**: Error messages, return values, or other contextual information.

The activity log is the primary tool for debugging failed commands and understanding what happened
during execution.

### 13.2 Audit Trail

The `command` table itself serves as the audit trail:

- **Who**: `initiated_by_ip` and `initiated_by_user` identify the requester.
- **What**: `command_type` and `tag_filter` describe the action.
- **When**: `created_at`, `started_at`, `completed_at` provide timing.
- **Outcome**: `status` and `error_summary` describe the result.

All commands are retained indefinitely (no automatic purging).

---

## 14. Validation

### 14.1 Post-Command Validation

After a command's workflow completes (but before the final `NotifyNode`), the `ValidateNode` queries
the NVR to verify that each camera's actual bitmask configuration matches the expected values.

**Process:**

1. For each camera that was configured during the workflow:
   a. Query the NVR for the camera's current notification bitmask (per detection type).
   b. Query the NVR for the camera's current zone mask (per detection type).
   c. Compare actual values to the values that were sent during the workflow.
2. Log any discrepancies to the `activity_log` with status `failed` and the details of the
   mismatch.
3. Include discrepancies in the notification sent by `NotifyNode`.

Validation discrepancies do **not** change the command status to `failed` — they are reported as
warnings. The command may still be `succeeded` or `completed_with_errors` (if there were other
failures).

---

## 15. Web UI

### 15.1 Technology

- **FastAPI** route handlers return **Jinja2** server-rendered HTML.
- **HTMX** provides dynamic behavior (form submissions, polling, partial page updates) without
  a JavaScript framework.
- **Tailwind CSS** handles all styling. CDN in development; built/purged CSS in production.

### 15.2 Pages

#### Dashboard (`/`)
- Current mode indicator (Home / Away) with visual distinction.
- Last command summary (type, status, time).
- Quick-action buttons: Set Away Now, Set Home Now.
- Active command progress (if a command is running).

#### Devices (`/devices`)
- **List** (`/devices`): Table of all devices with name, type, brand, channel, tags, enabled
  status.
- **Detail** (`/devices/{id}`): Full device information, detection types, bitmask assignments,
  associated power device, activity history.
- **Create/Edit** (`/devices/{id}/edit`): Form for device properties. Inline tag management.
  Detection type checkboxes.

#### Bitmasks (`/bitmasks`)
- **List** (`/bitmasks`): Table of all hour bitmasks and zone masks.
- **Hour Bitmask Detail** (`/bitmasks/hour/{id}`): Visual 24-hour timeline showing active hours.
  For dynamic bitmasks: shows today's calculated value.
- **Zone Mask Detail** (`/bitmasks/zone/{id}`): Visual 80x60 grid representation.
- **Create/Edit** forms for both types.

#### Tags (`/tags`)
- List of all tags with device count.
- Create/delete tags.
- Assign/remove tags from devices.

#### Command Execution (`/commands/execute`)
- **Set Away**: "Set Away Now" button and "Set Away in X Minutes" form.
- **Set Home**: "Set Home Now" button.
- **Pause Notifications**: Tag filter dropdown, duration input, "Pause" button.
- **Pause Recording**: Tag filter dropdown, duration input, "Pause" button.
- Optional `?user=` parameter input for audit trail.

#### Command History (`/commands`)
- Paginated list of all commands.
- Columns: ID, type, status, initiated by, created at, duration.
- Click-through to command detail.

#### Command Detail (`/commands/{id}`)
- Full command information.
- Activity log entries for this command (grouped by device).
- Validation results.

#### Activity Log (`/activity`)
- Searchable/filterable log viewer.
- Filters: command ID, device, date range, status.
- Sortable columns.

#### Admin (`/admin`)
- **Query NVR Cameras**: Button to query the NVR and display all connected cameras with their
  current metadata.
- **Pending Jobs**: List of SAQ jobs currently queued or scheduled.
- **Audit Trail**: Searchable list of all commands with full audit information.

### 15.3 HTMX Patterns

| Pattern | Usage |
|---|---|
| `hx-post` / `hx-put` | Form submissions (device edit, command execution) |
| `hx-get` with `hx-trigger="every 2s"` | Polling for command progress on dashboard |
| `hx-swap="innerHTML"` | Default swap for form responses and list updates |
| `hx-swap-oob` | Out-of-band swaps for toast notifications |
| `hx-target` | Targeting specific page sections for partial updates |
| `hx-confirm` | Confirmation dialogs for destructive actions |

### 15.4 User Identification

User identification is for **audit purposes only** — there is no authentication or authorization.
All users on the local network have full access.

Methods:
- `?user=` query parameter on command execution requests.
- The request IP address is always recorded.

> **Future options**: A user table with credentials (optional login), or an IP-to-username mapping
> table for automatic identification of local network users.

---

## 16. Hardware Integration

### 16.1 Reolink NVR (reolink-aio)

**Connection management**: The `reolink-aio` library provides an async client for the Reolink API.
The workflow manages login/logout as explicit nodes to ensure sessions are properly opened and
closed.

**Operations via reolink-aio:**
- Login / logout
- List channels (cameras connected to the NVR)
- Get camera info (model, firmware, resolution, etc.)
- PTZ control (move to preset, set speed)

**Operations that may require direct HTTP API calls** (if reolink-aio doesn't expose them):
- `SetAlarmParam` / `GetAlarmParam`: Set/get notification schedule bitmasks per detection type.
- Detection zone configuration: Set/get the 80x60 zone mask per detection type.
- Recording schedule configuration.

For direct API calls, the app will use `httpx` to make HTTP POST requests to the NVR's API
endpoint, using the session token obtained from reolink-aio's login.

### 16.2 Tapo Smart Plugs (python-kasa)

The `python-kasa` library provides async control of TP-Link Kasa and Tapo devices.

**Operations:**
- `turn_on()`: Power on the device.
- `turn_off()`: Power off the device.
- `update()` + `is_on`: Check power state.

Devices are identified by IP address. The library handles discovery and authentication
automatically.

### 16.3 Sonoff Mini R2 (HTTP API)

The Sonoff Mini R2 provides a simple HTTP API when in DIY mode.

**Operations:**
- `POST http://{ip}:8081/zeroconf/switch` with `{"data": {"switch": "on"}}`: Power on.
- `POST http://{ip}:8081/zeroconf/switch` with `{"data": {"switch": "off"}}`: Power off.
- `POST http://{ip}:8081/zeroconf/info` with `{"data": {}}`: Get device info including switch
  state.

Calls are made via `httpx`.

---

## 17. Docker & Deployment

### 17.1 Docker Compose

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data        # SQLite database
      - ./logs:/app/logs        # Log files
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

### 17.2 Dockerfile

```dockerfile
FROM python:3.14-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ src/

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Configurable UID/GID
ARG PUID=1000
ARG PGID=1000
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -m appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "remander.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 17.3 Logging

- **Dual output**: All logs are written to both stdout (for Docker log aggregation) and file
  (`LOG_DIR/remander.log`).
- **Rotation**: Weekly rotation via logrotate (or Python's `RotatingFileHandler`). Old logs are
  compressed with gzip.
- **Format**: Structured log format with timestamp, level, logger name, and message.

---

## 18. Development Workflow

### 18.1 Makefile Targets

| Target | Command | Description |
|---|---|---|
| `dev` | `docker compose up --build` | Start development environment |
| `prod` | `docker compose -f docker-compose.yml up -d` | Start production environment |
| `test` | `uv run pytest` | Run test suite |
| `lint` | `uv run ruff check .` | Run linter |
| `format` | `uv run ruff format .` | Format code |
| `migrate` | `uv run aerich migrate && uv run aerich upgrade` | Run database migrations |
| `logs` | `docker compose logs -f app` | Tail application logs |

### 18.2 Testing

- **Framework**: pytest + pytest-asyncio
- **Mocked hardware**: All NVR, Tapo, and Sonoff interactions are mocked in tests. No real
  hardware required for the test suite.
- **Factory fixtures**: Reusable pytest fixtures that create test devices, bitmasks, commands, etc.
  with sensible defaults.
- **Coverage target**: 100% line coverage for business logic. Hardware client wrappers are
  excluded from coverage (tested via integration tests against real hardware).

### 18.3 Code Quality

- **Ruff**: Configured for Black-compatible formatting + isort import sorting.
- **Line length**: 100 characters.
- **Type checking**: Full type annotations on all functions and classes. Type checking via mypy or
  pyright (TBD).

---

## 19. Future Considerations

These items are explicitly **out of scope** for the initial implementation but the architecture
should not preclude them:

- **PostgreSQL migration**: Tortoise ORM supports PostgreSQL with minimal code changes. The
  `DATABASE_URL` setting already supports this.
- **Multiple NVRs**: The data model could be extended with an `nvr` table and a `device.nvr_id`
  foreign key.
- **Additional notification providers**: The `NotificationSender` protocol makes adding Pushover,
  webhooks, etc. straightforward.
- **Geofencing**: Automatic mode switching based on phone location.
- **Command interruptibility matrix**: A configuration that defines which command types can
  interrupt which other command types (e.g., "Set Away Now" can interrupt "Pause Notifications"
  but not vice versa).
- **Authentication**: Optional login system for multi-user households.
- **Camera live view**: Embedding RTSP streams or snapshots in the UI.

---

## 20. Milestones

### Milestone 1: Foundation & Project Setup

**Goal**: Everything needed before business logic begins.

| Task | Description |
|---|---|
| Project scaffolding | `uv init`, `pyproject.toml`, directory structure (`src/remander/`) |
| Docker Compose | App + Redis containers, Dockerfile, `.dockerignore` |
| Configuration | pydantic-settings with `.env.example` |
| Database setup | Tortoise ORM initialization + Aerich migrations |
| Database models | All tables from Section 6 |
| Logging | Configurable format, dual output (stdout + file), rotation |
| Makefile | `dev`, `prod`, `test`, `lint`, `format`, `migrate`, `logs` targets |
| Test infrastructure | `conftest.py`, async fixtures, factory helpers |
| FastAPI app | Basic app with health-check endpoint (`/health`) |

**Exit criteria**: `make dev` starts the app, `make test` runs (empty) tests, database tables are
created via migration, health-check returns 200.

---

### Milestone 2: Core Backend — Devices, Bitmasks, Hardware

**Goal**: CRUD operations and hardware integration (no commands or workflows yet).

| Task | Description |
|---|---|
| Device service | CRUD operations for cameras and power devices |
| Tag service | CRUD for tags, assign/remove tags from devices |
| Detection type service | Enable/disable detection types per device |
| Bitmask service | CRUD for hour bitmasks (static + dynamic) and zone masks |
| Sunrise/sunset calculation | Dynamic bitmask resolution using astral library |
| Reolink NVR client | Login/logout, list channels, get/set alarm schedules, get/set detection zones, PTZ operations |
| Tapo client | Power on/off/status via python-kasa |
| Sonoff client | Power on/off/status via HTTP API |
| Tests | Unit + integration tests for all services and clients |

**Exit criteria**: All device/bitmask/tag CRUD works end-to-end. NVR, Tapo, and Sonoff clients
have passing tests (mocked hardware). Dynamic bitmask calculation produces correct results.

---

### Milestone 3: Command & Workflow Engine

**Goal**: The core intelligence — commands, workflows, scheduling, validation, notifications.

| Task | Description |
|---|---|
| SAQ worker | Redis-backed worker integrated with FastAPI lifespan |
| Command service | Create commands, state machine transitions, queue management |
| Workflow nodes | All reusable nodes from Section 10.1 |
| Set Away workflow | Full pydantic-graph implementation |
| Set Home workflow | Full pydantic-graph implementation |
| Pause Notifications workflow | Full pydantic-graph implementation |
| Pause Recording workflow | Full pydantic-graph implementation |
| Re-Arm workflow | Full pydantic-graph implementation |
| Command queueing | FIFO queue, one-at-a-time execution |
| Delayed commands | SAQ scheduled jobs for Set Away Delayed |
| Re-arm scheduling | SAQ timer jobs for pause commands |
| Validation service | Post-command NVR verification |
| Notification sender | Email (SMTP) implementation with templates |
| Activity logging | Per-node, per-device logging throughout workflows |
| Tests | Full test coverage for all workflows (mocked hardware) |

**Exit criteria**: All five command types execute correctly end-to-end (in tests). Commands queue
properly. Delayed and re-arm timers fire correctly. Notifications send. Activity log captures all
steps.

---

### Milestone 4: Web UI

**Goal**: All user-facing pages.

> **Note**: CRUD UI pages (devices, bitmasks, tags) can begin as soon as Milestone 2 is complete,
> in parallel with Milestone 3 work.

| Task | Description |
|---|---|
| Base template | Jinja2 layout with Tailwind CSS + HTMX includes, navigation |
| Dashboard | Current mode, last command, quick actions, active command progress |
| Device pages | List, detail, create/edit with tag and detection type management |
| Bitmask pages | List, detail, create/edit for hour bitmasks and zone masks; dynamic preview |
| Tag management | List, create, delete; device association |
| Command execution | Set Away/Home buttons, Pause controls with tag filter and duration |
| Command history | Paginated list with click-through to detail |
| Command detail | Full info + activity log entries grouped by device |
| Activity log viewer | Filterable by command, device, date range |
| Admin: Query NVR | Button to query NVR and display camera metadata |
| Admin: Pending jobs | List of SAQ jobs queued or scheduled |
| Admin: Audit trail | Searchable command history with full audit info |
| HTMX integration | Polling for progress, toast notifications, inline editing |

**Exit criteria**: All pages render correctly. Commands can be initiated from the UI. Progress
updates in real time. Activity logs and audit trail are browsable.
