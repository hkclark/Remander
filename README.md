# Remander

A home automation app that configures Reolink security cameras for different behavior when "at home" vs "away from home" using the Reolink NVR API. Also controls Tapo smart plugs and Sonoff Mini R2 switches.

See `spec.md` for the full project specification.

## Quick Start

```bash
# Install dependencies
uv sync

# Start Redis (required for job queue)
make redis-up

# Initialize the database (first time only)
make migrate-init

# Run the app with auto-reload
make run-dev
```

## Database Migrations

Remander uses [Aerich](https://github.com/tortoise/aerich) (Tortoise ORM's migration tool) to manage database schema changes. All schema changes must go through aerich — the app does not auto-create or modify tables on startup.

### Setting up a new system

When starting fresh (no database exists yet):

```bash
make migrate-init
```

This runs `aerich init-db`, which creates the database, applies the initial migration, and seeds aerich's internal tracking table. Only run this once per database.

### Adding a new migration

When you've changed a model (added a field, renamed a column, etc.):

```bash
make migrate
```

This runs `aerich migrate` to detect model changes and generate a new migration file in `migrations/models/`, then runs `aerich upgrade` to apply it. Review the generated migration file before committing.

### Applying migrations to an existing system

When pulling code that includes new migration files:

```bash
uv run aerich upgrade
```

This applies any unapplied migrations to the database. The `make migrate` target also works — `aerich migrate` will report "No changes detected" and `aerich upgrade` will apply the pending files.

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
| `make migrate` | Generate and apply database migrations |
| `make migrate-init` | Initialize database from scratch |
