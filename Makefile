.PHONY: help run run-dev redis-up redis-down test lint format migrate transcripts transcripts-all

.DEFAULT_GOAL := help

-include .env
-include .env.dev
export

## Show this help message
help:
	@awk '/^## /{desc=substr($$0,4)} /^[a-zA-Z_-]+:/{if(desc){sub(/:.*/, "", $$1); printf "  \033[36m%-20s\033[0m %s\n", $$1, desc; desc=""}}' $(MAKEFILE_LIST)

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

## Generate (if needed) and apply database migrations
migrate:
	@uv run aerich migrate 2>/dev/null || true
	uv run aerich upgrade

## Show auto-exported session transcripts
transcripts:
	@./scripts/list-transcripts.sh

## Show all transcripts including raw ones from ~/.claude/projects/
transcripts-all:
	@./scripts/list-transcripts.sh --all
