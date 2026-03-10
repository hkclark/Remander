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

There are two distinct operations, each with its own make target:

### Applying migrations (fresh install or pulling new code)

```bash
make migrate
```

Runs `aerich upgrade`, which applies all pending migration files in order. Works for:
- **Fresh install**: SQLite creates the database file automatically, aerich applies every migration from scratch
- **Pulling new code**: applies any migration files that aren't in your database yet

### Creating a new migration (after changing a model)

The `DATABASE_URL` in `.env` points to the Docker container path (`/app/data/remander.db`),
which doesn't exist when running locally. To generate migrations outside Docker, use a temp local DB:

```bash
# 1. Make your model changes in src/remander/models/

# 2. Create a local temp DB and apply all existing migrations to it
mkdir -p /tmp/remander_migration
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich upgrade

# 3. Try to generate the migration (this may fail with NotSupportError on SQLite — see note below)
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich migrate --name add_foo_field

# If step 3 failed with "NotSupportError: Alter column comment is unsupported in SQLite",
# use --empty instead to generate a shell with the correct MODELS_STATE, then add SQL manually:
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich migrate --name add_foo_field --empty

# 4. Open the generated file in migrations/models/ and add the SQL to upgrade()/downgrade()

# 5. Apply it to verify the SQL is correct
DATABASE_URL="sqlite:////tmp/remander_migration/remander.db" uv run aerich upgrade
```

**Never write migration files by hand** — the `MODELS_STATE` blob must come from aerich's own
tooling. Always use `aerich migrate` (or `aerich migrate --empty`) to get the correct MODELS_STATE,
then add SQL if needed. Manually writing or splitting the MODELS_STATE string corrupts it.

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
| `make migrate` | Apply all pending migrations (`aerich upgrade`) |
