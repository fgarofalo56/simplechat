# Makefile
# Developer workflow targets for SimpleChat.
# Run `make help` for available commands.

.DEFAULT_GOAL := help
SHELL := /bin/bash

APP_DIR := application/single_app
PYTHON := python3
PIP := pip3

# =================== Help ===================
.PHONY: help
help: ## Show this help message
	@echo "SimpleChat Development Commands"
	@echo "==============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =================== Setup ===================
.PHONY: install
install: ## Install all dependencies (production + dev)
	cd $(APP_DIR) && $(PIP) install -r requirements.txt
	cd $(APP_DIR) && $(PIP) install -r requirements-dev.txt

.PHONY: install-prod
install-prod: ## Install production dependencies only
	cd $(APP_DIR) && $(PIP) install -r requirements.txt

# =================== Development ===================
.PHONY: dev
dev: ## Run the Flask development server
	cd $(APP_DIR) && $(PYTHON) -m flask run --debug --port 5000

.PHONY: run
run: ## Run with gunicorn (production-like)
	cd $(APP_DIR) && $(PYTHON) -m gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 app:app

# =================== Testing ===================
.PHONY: test
test: ## Run all tests with coverage
	cd $(APP_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

.PHONY: test-unit
test-unit: ## Run unit tests only
	cd $(APP_DIR) && $(PYTHON) -m pytest tests/unit/ -v --tb=short

.PHONY: test-integration
test-integration: ## Run integration tests only
	cd $(APP_DIR) && $(PYTHON) -m pytest tests/integration/ -v --tb=short

.PHONY: test-quick
test-quick: ## Run tests without coverage (faster)
	cd $(APP_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short -q

.PHONY: coverage
coverage: ## Generate HTML coverage report
	cd $(APP_DIR) && $(PYTHON) -m pytest tests/ --cov=. --cov-report=html
	@echo "Coverage report: $(APP_DIR)/htmlcov/index.html"

# =================== Linting ===================
.PHONY: lint
lint: ## Run ruff linter
	cd $(APP_DIR) && $(PYTHON) -m ruff check .

.PHONY: lint-fix
lint-fix: ## Run ruff linter with auto-fix
	cd $(APP_DIR) && $(PYTHON) -m ruff check . --fix

.PHONY: format
format: ## Run ruff formatter
	cd $(APP_DIR) && $(PYTHON) -m ruff format .

.PHONY: format-check
format-check: ## Check code formatting without modifying
	cd $(APP_DIR) && $(PYTHON) -m ruff format --check .

# =================== Security ===================
.PHONY: security
security: ## Run pip-audit for dependency vulnerabilities
	cd $(APP_DIR) && $(PYTHON) -m pip_audit --strict --desc

# =================== Docker ===================
.PHONY: docker-build
docker-build: ## Build the Docker image
	docker build -t simplechat:latest .

.PHONY: docker-run
docker-run: ## Run the Docker container
	docker run -p 5000:5000 --env-file $(APP_DIR)/.env simplechat:latest

.PHONY: compose-up
compose-up: ## Start all services with docker compose
	docker compose up -d

.PHONY: compose-down
compose-down: ## Stop all docker compose services
	docker compose down

.PHONY: compose-logs
compose-logs: ## Follow docker compose logs
	docker compose logs -f app

.PHONY: compose-rebuild
compose-rebuild: ## Rebuild and restart docker compose services
	docker compose down && docker compose up -d --build

# =================== Cleanup ===================
.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf $(APP_DIR)/temp/ 2>/dev/null || true
