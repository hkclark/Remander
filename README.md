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

`make migrate` is the single command for all migration scenarios:

### Setting up a new system

When starting fresh (no database exists yet):

```bash
make migrate
```

This creates the database, applies all migration files, and sets up aerich's internal tracking table.

### Adding a new migration

When you've changed a model (added a field, renamed a column, etc.):

```bash
make migrate
```

This detects model changes, generates a new migration file in `migrations/models/`, and applies it. Review the generated migration file before committing.

### Applying migrations to an existing system

When pulling code that includes new migration files:

```bash
make migrate
```

This applies any unapplied migrations to the database.

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
| `make migrate` | Generate (if needed) and apply database migrations |
