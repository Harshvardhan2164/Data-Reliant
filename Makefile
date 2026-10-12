.PHONY: help install dev lint format typecheck test test-unit test-integration test-e2e \
       coverage migrate migrate-create up down build clean generate-data evaluate docs

# ── Variables ────────────────────────────────────────────────────────
PYTHON := python
PIP := pip
DOCKER_COMPOSE := docker compose

# ── Help ─────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Installation ─────────────────────────────────────────────────────
install: ## Install production dependencies
	$(PIP) install -e .

dev: ## Install development dependencies
	$(PIP) install -e ".[dev,notebooks]"
	pre-commit install || true

# ── Code Quality ─────────────────────────────────────────────────────
lint: ## Run linter
	ruff check datareliant/ apps/ generators/ tests/

format: ## Format code
	ruff format datareliant/ apps/ generators/ tests/
	ruff check --fix datareliant/ apps/ generators/ tests/

typecheck: ## Run type checker
	mypy datareliant/ apps/api/

# ── Testing ──────────────────────────────────────────────────────────
test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests
	pytest tests/integration/ -v -m integration

test-e2e: ## Run end-to-end tests
	pytest tests/end_to_end/ -v -m e2e

coverage: ## Run tests with coverage
	pytest tests/ --cov=datareliant --cov-report=html --cov-report=term-missing

# ── Database ─────────────────────────────────────────────────────────
migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade: ## Downgrade one migration
	alembic downgrade -1

# ── Docker ───────────────────────────────────────────────────────────
up: ## Start all services
	$(DOCKER_COMPOSE) up -d

down: ## Stop all services
	$(DOCKER_COMPOSE) down

build: ## Build Docker images
	$(DOCKER_COMPOSE) build

logs: ## Show service logs
	$(DOCKER_COMPOSE) logs -f

# ── Data & Experiments ───────────────────────────────────────────────
generate-data: ## Generate synthetic datasets
	$(PYTHON) -m generators.normal_data.generate

inject-failures: ## Inject failure scenarios
	$(PYTHON) -m generators.anomaly_injection.inject

evaluate: ## Run evaluation against all scenarios
	$(PYTHON) -m datareliant.cli evaluate --scenario all

# ── Cleanup ──────────────────────────────────────────────────────────
clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# ── Documentation ────────────────────────────────────────────────────
docs: ## Build documentation (placeholder)
	@echo "Documentation build not yet configured."

# ── API Server (local, no Docker) ────────────────────────────────────
serve: ## Run API server locally
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
