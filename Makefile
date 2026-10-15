.PHONY: install up down infra api web pms market-data pms-load test lint fmt

install:            ## Install all dependencies
	cd apps/api && uv sync
	cd apps/legacy-pms && uv sync
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

pms:                ## Run legacy PMS API (:8100)
	cd apps/legacy-pms && uv run uvicorn hc_pms.main:app --reload --port 8100

market-data:        ## Download prices/dividends/FX for data/universe.csv into data/raw/market
	cd data && uv run --no-project --with yfinance python scripts/fetch_market_data.py

pms-load:           ## (Re)build the PMS database: reference + market data + synthetic firm
	cd apps/legacy-pms && uv run hc-pms-load --universe ../../data/universe.csv --market-dir ../../data/raw/market --reset

test:
	cd apps/api && uv run pytest -q
	cd apps/legacy-pms && uv run pytest -q

lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run pyright
	cd apps/legacy-pms && uv run ruff check . && uv run ruff format --check . && uv run pyright
	pnpm lint:web

fmt:
	cd apps/api && uv run ruff format . && uv run ruff check --fix .
	cd apps/legacy-pms && uv run ruff format . && uv run ruff check --fix .
