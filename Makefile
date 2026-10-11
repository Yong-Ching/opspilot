.PHONY: install up down infra api web test lint fmt

install:            ## Install all dependencies
	cd apps/api && uv sync
	pnpm install
	pre-commit install

up:                 ## Start the whole stack in Docker
	docker compose up --build -d

down:
	docker compose down

infra:              ## Start only Postgres + Redis (for local dev with hot reload)
	docker compose up -d postgres redis

api:                ## Run API with hot reload
	cd apps/api && uv run uvicorn opspilot_api.main:app --reload --port 8000

web:                ## Run web with hot reload
	pnpm dev:web

test:
	cd apps/api && uv run pytest -q

lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run pyright
	pnpm lint:web

fmt:
	cd apps/api && uv run ruff format . && uv run ruff check --fix .
