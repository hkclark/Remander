.PHONY: dev prod test lint format migrate logs transcripts transcripts-all

## Start development environment
dev:
	docker compose up --build

## Start production environment (detached)
prod:
	docker compose up -d

## Run test suite
test:
	uv run pytest

## Run linter
lint:
	uv run ruff check .

## Format code
format:
	uv run ruff format .

## Run database migrations
migrate:
	uv run aerich migrate && uv run aerich upgrade

## Tail application logs
logs:
	docker compose logs -f app

## Show auto-exported session transcripts
transcripts:
	@./scripts/list-transcripts.sh

## Show all transcripts including raw ones from ~/.claude/projects/
transcripts-all:
	@./scripts/list-transcripts.sh --all
