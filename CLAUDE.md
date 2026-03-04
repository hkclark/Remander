# Project Context

When working with this codebase, prioritize readability over cleverness. Ask clarifying questions before making architectural changes.

See `spec.md` for the full project specification (architecture, data model, workflows, UI, milestones).

## About This Project

A home automation app ("Remander") that primarily configures Reolink security cameras for different
behavior when "at home" vs "away from home" (e.g., configure the cameras to provide limited notifications
when the user is "at home" but have full notifications when they are away from home) by using the Reolink
NVR API. It also controls non-Reolink power devices such as Tapo smart plugs and Sonoff Mini R2
switches (e.g., to power on cameras that are off when "at home").

## Project Structure

```
src/remander/          # Application source code
  main.py              # FastAPI app entrypoint
  config.py            # pydantic-settings configuration
  models/              # Tortoise ORM models
  routes/              # FastAPI route handlers
  services/            # Business logic layer
  clients/             # Hardware clients (NVR, Tapo, Sonoff)
  workflows/           # Pydantic AI graph workflows
  templates/           # Jinja2 HTML templates
tests/                 # pytest test suite
  factories/           # Test factory fixtures
```

## Standards

- Python 3.14
- Use full type annotation with the latest annotation styles (e.g., prefer "int | None" over "Optional[int]")
- pytest + pytest-asyncio for testing
- Ruff for linting and formatting (Black-compatible, 100 character lines)
- Assume we are using the latest version of all frameworks, libraries and tools unless otherwise specifically stated
- Use fully async Python code as much as possible

### Testing Methodology

- Follow **red/green TDD** (Test-Driven Development):
  1. **RED**: Write a failing test for the next piece of functionality
  2. **GREEN**: Write the minimum code to make the test pass
  3. **REFACTOR**: Clean up the code while keeping tests green
- When starting a new service or component, create the test file first
- Keep the red/green cycle small — one function or one behavior at a time
- Verify tests actually fail before writing implementation (the RED step matters)

## Class System

- **attrs**: Domain objects, value objects, utility classes (default choice)
- **Pydantic**: API request/response models, pydantic-settings config, workflow state
- **Tortoise Model**: Database ORM models
- If a class doesn't use attrs, add a comment at the top explaining why (e.g., `# Reason: Pydantic model for API validation`)

## Frameworks, Tools, & Libraries

- Package manager: uv
- Web UI/Frontend:
  - FastAPI
  - Server-side rendered Jinja2 templates
  - HTMX "hypermedia first" approach
  - Tailwind CSS for styling
- Backend:
  - SQLite database (PostgreSQL-ready via Tortoise ORM)
  - Tortoise ORM + Aerich migrations
  - Pydantic AI (pydantic-graph) as a workflow engine for commands
  - SAQ + Redis for job queue and scheduling
  - pydantic-settings for configuration
- Hardware integration:
  - reolink-aio for Reolink NVR communication
  - python-kasa for Tapo smart plug control
  - httpx for Sonoff Mini R2 HTTP API
- Other:
  - astral for sunrise/sunset calculation
  - aiosmtplib for email notifications
  - attrs for domain classes
