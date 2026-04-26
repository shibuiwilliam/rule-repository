.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
SERVER_DIR   := apps/server
FRONTEND_DIR := apps/frontend
CLIENT_DIR   := packages/rule-client
AGENTIC_DIR  := packages/agentic-client
SERVER_URL   ?= http://localhost:8000

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-24s\033[0m %s\n", $$1, $$2}' | \
		sort

# ===========================================================================
#  Setup
# ===========================================================================
.PHONY: setup env install install.server install.frontend install.client

setup: env install ## First-time project setup (create .env + install all deps)

env: ## Create .env from .env.example (won't overwrite existing)
	@test -f .env || (cp .env.example .env && echo ".env created — fill in GEMINI_API_KEY")
	@test -f .env && echo ".env already exists"

install: install.server install.frontend install.client ## Install all dependencies

install.server: ## Install backend dependencies
	cd $(SERVER_DIR) && uv sync

install.frontend: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && pnpm install

install.client: ## Install SDK dependencies
	cd $(CLIENT_DIR) && uv sync
	cd $(AGENTIC_DIR) && uv sync

# ===========================================================================
#  Docker Compose — full stack
# ===========================================================================
.PHONY: up down restart logs logs.server logs.frontend ps build

up: ## Start the full stack (docker compose up --build -d)
	docker compose up --build -d

down: ## Stop the full stack
	docker compose down

down.clean: ## Stop the full stack and wipe all volumes
	docker compose down -v

restart: down up ## Restart the full stack

build: ## Build all Docker images without starting
	docker compose build

ps: ## Show running services
	docker compose ps

logs: ## Tail logs for all services
	docker compose logs -f

logs.server: ## Tail backend server logs
	docker compose logs -f server

logs.frontend: ## Tail frontend logs
	docker compose logs -f frontend

logs.db: ## Tail all database logs (postgres, elasticsearch, neo4j)
	docker compose logs -f postgres elasticsearch neo4j

# ===========================================================================
#  Local dev — run services outside Docker
# ===========================================================================
.PHONY: dev.server dev.frontend

dev.server: ## Run backend dev server (hot-reload, port 8000)
	cd $(SERVER_DIR) && uv run uvicorn rulerepo_server.main:app --reload --host 0.0.0.0 --port 8000

dev.frontend: ## Run frontend dev server (hot-reload, port 3000)
	cd $(FRONTEND_DIR) && pnpm dev

# ===========================================================================
#  Lint & Format
# ===========================================================================
.PHONY: lint lint.server lint.frontend format format.server format.check

lint: lint.server lint.frontend ## Lint everything

lint.server: ## Lint Python code (ruff + mypy)
	cd $(SERVER_DIR) && uv run ruff check src/ tests/
	cd $(SERVER_DIR) && uv run mypy src/

lint.frontend: ## Lint frontend code (ESLint + TypeScript)
	cd $(FRONTEND_DIR) && pnpm lint
	cd $(FRONTEND_DIR) && pnpm typecheck

format: format.server ## Format all code

format.server: ## Format Python code (ruff)
	cd $(SERVER_DIR) && uv run ruff format src/ tests/
	cd $(SERVER_DIR) && uv run ruff check --fix src/ tests/

format.check: ## Check formatting without modifying files
	cd $(SERVER_DIR) && uv run ruff format --check src/ tests/
	cd $(SERVER_DIR) && uv run ruff check src/ tests/

# ===========================================================================
#  Test
# ===========================================================================
.PHONY: test test.server test.frontend test.client test.unit test.integration test.verbose

test: test.server test.frontend ## Run all tests

test.server: ## Run backend tests
	cd $(SERVER_DIR) && uv run pytest

test.frontend: ## Run frontend tests
	cd $(FRONTEND_DIR) && pnpm test

test.client: ## Run SDK tests
	cd $(CLIENT_DIR) && uv run pytest

test.unit: ## Run backend unit tests only
	cd $(SERVER_DIR) && uv run pytest tests/unit/

test.integration: ## Run backend integration tests only
	cd $(SERVER_DIR) && uv run pytest tests/integration/

test.verbose: ## Run all backend tests with verbose output
	cd $(SERVER_DIR) && uv run pytest -v --tb=short

test.cov: ## Run backend tests with coverage report
	cd $(SERVER_DIR) && uv run pytest --cov=rulerepo_server --cov-report=term-missing

# ===========================================================================
#  Database
# ===========================================================================
.PHONY: db.migrate db.rollback db.heads db.history db.revision

db.migrate: ## Run Alembic migrations to latest
	cd $(SERVER_DIR) && uv run alembic upgrade head

db.rollback: ## Roll back one Alembic migration
	cd $(SERVER_DIR) && uv run alembic downgrade -1

db.heads: ## Show current Alembic heads
	cd $(SERVER_DIR) && uv run alembic heads

db.history: ## Show Alembic migration history
	cd $(SERVER_DIR) && uv run alembic history --verbose

db.revision: ## Create a new Alembic migration (usage: make db.revision MSG="add foo table")
	cd $(SERVER_DIR) && uv run alembic revision --autogenerate -m "$(MSG)"

# ===========================================================================
#  Scripts & Data
# ===========================================================================
.PHONY: seed reconcile

seed: ## Load sample rules into a running stack
	uv run python scripts/seed_data.py

reconcile: ## Rebuild Neo4j graph from PostgreSQL source of truth
	uv run python scripts/reconcile_graph.py

# ===========================================================================
#  MCP Server
# ===========================================================================
.PHONY: mcp.stdio mcp.http

mcp.stdio: ## Run MCP server in stdio mode (for Claude Code / local agents)
	cd $(SERVER_DIR) && uv run rulerepo-mcp

mcp.http: ## Run MCP server in HTTP mode (port 8001)
	cd $(SERVER_DIR) && MCP_TRANSPORT=streamable-http MCP_PORT=8001 uv run rulerepo-mcp

# ===========================================================================
#  Build & Package
# ===========================================================================
.PHONY: build.server build.frontend build.client build.all

build.server: ## Build backend Docker image
	docker compose build server

build.frontend: ## Build frontend Docker image
	docker compose build frontend

build.client: ## Build Python SDK wheel
	cd $(CLIENT_DIR) && uv build

build.all: build.server build.frontend build.client ## Build everything

# ===========================================================================
#  Health & Status
# ===========================================================================
.PHONY: health ready api.health

health: ## Check backend liveness
	@curl -sf $(SERVER_URL)/healthz | python3 -m json.tool || echo "Backend not reachable at $(SERVER_URL)"

ready: ## Check backend readiness (postgres, elasticsearch, neo4j)
	@curl -sf $(SERVER_URL)/readyz | python3 -m json.tool || echo "Backend not reachable at $(SERVER_URL)"

api.health: ## Check API health
	@curl -sf $(SERVER_URL)/api/v1/health | python3 -m json.tool || echo "API not reachable at $(SERVER_URL)"

# ===========================================================================
#  Quality gates — run before committing
# ===========================================================================
.PHONY: check ci

check: format.check lint test ## Run all quality checks (format + lint + test)

ci: install check ## Full CI pipeline (install + format + lint + test)

# ===========================================================================
#  Cleanup
# ===========================================================================
.PHONY: clean clean.python clean.frontend clean.docker

clean: clean.python clean.frontend ## Remove all build artifacts

clean.python: ## Remove Python caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

clean.frontend: ## Remove frontend build artifacts
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/node_modules/.cache

clean.docker: ## Remove all project Docker images and volumes
	docker compose down -v --rmi local 2>/dev/null || true
