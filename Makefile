.PHONY: run run-dev redis-up redis-down test lint format migrate migrate-init transcripts transcripts-all

-include .env
-include .env.dev
export

## Start Redis (if needed) + run app locally
run: redis-up
	uv run uvicorn remander.main:app --host 0.0.0.0 --port 8000

## Start Redis (if needed) + run app locally with auto-reload
run-dev: redis-up
	uv run uvicorn remander.main:app --host 0.0.0.0 --port 8000 --reload

## Start dev Redis container (detached)
redis-up:
	@docker compose -f docker-compose.dev.yml up -d redis

## Stop dev Redis container
redis-down:
	@docker compose -f docker-compose.dev.yml down

## Run test suite
test:
	uv run pytest

## Run linter
lint:
	uv run ruff check .

## Format code
format:
	uv run ruff format .

## Generate and apply pending database migrations
migrate:
	uv run aerich migrate && uv run aerich upgrade

## Initialize database from scratch (new system or fresh start)
migrate-init:
	uv run aerich init-db

## Show auto-exported session transcripts
transcripts:
	@./scripts/list-transcripts.sh

## Show all transcripts including raw ones from ~/.claude/projects/
transcripts-all:
	@./scripts/list-transcripts.sh --all
