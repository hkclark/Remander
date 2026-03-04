# Milestone 1: Foundation & Project Setup

**Goal**: Everything needed before business logic begins.

**Exit criteria**: `make dev` starts the app, `make test` runs (empty) tests, database tables are
created via migration, health-check returns 200.

---

## Tasks

### 1. Project Scaffolding
- [ ] Initialize project with `uv init`
- [ ] Configure `pyproject.toml` (name, version, Python 3.14, dependencies)
- [ ] Create directory structure:
  ```
  src/
    remander/
      __init__.py
      main.py
      config.py
      models/
        __init__.py
      routes/
        __init__.py
      services/
        __init__.py
      clients/
        __init__.py
      workflows/
        __init__.py
      templates/
        __init__.py
  ```
- [ ] Add all dependencies to `pyproject.toml`:
  - fastapi, uvicorn, jinja2, python-multipart
  - tortoise-orm, aerich
  - pydantic, pydantic-settings
  - pydantic-ai (pydantic-graph)
  - saq, redis
  - reolink-aio, python-kasa, httpx
  - astral, aiosmtplib
  - attrs
  - ruff
  - pytest, pytest-asyncio
- [ ] Run `uv sync` to generate `uv.lock`

### 2. Configuration
- [ ] Create `src/remander/config.py` with pydantic-settings `Settings` class
- [ ] All settings from spec Section 5 (NVR, Redis, DB, SMTP, lat/long, logging, PUID/PGID, power-on timing)
- [ ] Create `.env.example` with documented defaults

### 3. Docker
- [ ] Create `Dockerfile` (Python 3.14-slim, uv, configurable UID/GID)
- [ ] Create `docker-compose.yml` (app + Redis containers, volumes for data/logs)
- [ ] Create `.dockerignore` (`.git`, `__pycache__`, `.env`, etc.)

### 4. Database Models
- [ ] Create `src/remander/models/enums.py` — all StrEnum types from spec Section 6
  - DeviceType, DeviceBrand, PowerDeviceSubtype, DetectionType
  - HourBitmaskSubtype, Mode, CommandType, CommandStatus, ActivityStatus
- [ ] Create `src/remander/models/device.py` — Device model
- [ ] Create `src/remander/models/tag.py` — Tag and DeviceTag models
- [ ] Create `src/remander/models/bitmask.py` — HourBitmask, ZoneMask, DeviceBitmaskAssignment models
- [ ] Create `src/remander/models/detection.py` — DeviceDetectionType model
- [ ] Create `src/remander/models/command.py` — Command model
- [ ] Create `src/remander/models/activity.py` — ActivityLog model
- [ ] Create `src/remander/models/state.py` — SavedDeviceState and AppState models
- [ ] Register all models in `src/remander/models/__init__.py`

### 5. Database Setup (Tortoise ORM + Aerich)
- [ ] Configure Tortoise ORM in FastAPI app (lifespan or startup/shutdown)
- [ ] Create `TORTOISE_ORM` config dict for Aerich
- [ ] Initialize Aerich (`aerich init`, `aerich init-db`)
- [ ] Verify migrations create all tables from spec Section 6

### 6. Logging
- [ ] Create `src/remander/logging.py` — logging setup function
- [ ] Dual output: stdout + file (`LOG_DIR/remander.log`)
- [ ] Configurable log level from settings
- [ ] TimedRotatingFileHandler (weekly rotation)
- [ ] Structured format: `%(asctime)s %(levelname)s %(name)s %(message)s`

### 7. FastAPI App
- [ ] Create `src/remander/main.py` — FastAPI app with lifespan
- [ ] Lifespan: initialize Tortoise ORM, configure logging
- [ ] Health-check endpoint: `GET /health` returns `{"status": "ok"}`
- [ ] Mount Jinja2 templates directory (empty for now)

### 8. Makefile
- [ ] `dev` — `docker compose up --build`
- [ ] `prod` — `docker compose -f docker-compose.yml up -d`
- [ ] `test` — `uv run pytest`
- [ ] `lint` — `uv run ruff check .`
- [ ] `format` — `uv run ruff format .`
- [ ] `migrate` — `uv run aerich migrate && uv run aerich upgrade`
- [ ] `logs` — `docker compose logs -f app`

### 9. Ruff Configuration
- [ ] Add `[tool.ruff]` section to `pyproject.toml`
- [ ] Line length: 100
- [ ] Black-compatible formatting
- [ ] isort import sorting
- [ ] Target Python 3.14

### 10. Test Infrastructure
- [ ] Create `tests/` directory
- [ ] Create `tests/conftest.py` with:
  - Async test configuration (pytest-asyncio)
  - Tortoise ORM test database setup/teardown (in-memory SQLite)
  - `AsyncClient` fixture for FastAPI test client
- [ ] Create `tests/test_health.py` — verify health-check returns 200
- [ ] Create `tests/factories/` directory with `__init__.py` (empty, ready for Milestone 2)
- [ ] Verify `make test` passes

### 11. Final Verification
- [ ] `make lint` passes with no errors
- [ ] `make format` produces no changes
- [ ] `make test` passes (health-check test)
- [ ] `make dev` starts the app and Redis containers
- [ ] `GET /health` returns 200
- [ ] Database tables are created on startup
