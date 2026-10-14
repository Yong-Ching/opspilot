.PHONY: install up down infra api web oms oms-data oms-load test lint fmt

install:            ## Install all dependencies
	cd apps/api && uv sync
	cd apps/legacy-oms && uv sync
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

oms:                ## Run legacy OMS API (:8100)
	cd apps/legacy-oms && uv run uvicorn acme_oms.main:app --reload --port 8100

oms-data:           ## Download the Olist dataset into data/raw/olist
	mkdir -p data/raw/olist
	curl -fL -o data/raw/olist.zip https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce
	unzip -oq data/raw/olist.zip -d data/raw/olist && rm data/raw/olist.zip

oms-load:           ## (Re)load Olist into the acme_oms database
	cd apps/legacy-oms && uv run acme-oms-load --data-dir ../../data/raw/olist --reset

test:
	cd apps/api && uv run pytest -q
	cd apps/legacy-oms && uv run pytest -q

lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run pyright
	cd apps/legacy-oms && uv run ruff check . && uv run ruff format --check . && uv run pyright
	pnpm lint:web

fmt:
	cd apps/api && uv run ruff format . && uv run ruff check --fix .
	cd apps/legacy-oms && uv run ruff format . && uv run ruff check --fix .
