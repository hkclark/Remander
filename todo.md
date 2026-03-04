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
