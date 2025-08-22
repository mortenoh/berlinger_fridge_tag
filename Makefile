# Berlinger Fridge Tag - Makefile

.PHONY: help test lint fmt install dev clean docker-build docker-run docker-stop docker-clean api cli

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Development setup
install: ## Install dependencies
	uv sync

dev: ## Install development dependencies
	uv sync --dev

# Testing
test: ## Run tests
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=berlinger_fridge_tag --cov-report=html --cov-report=term

# Code quality
lint: ## Run linting
	uv run ruff check .

fmt: ## Format code
	uv run ruff format .

fmt-check: ## Check formatting
	uv run ruff format --check .

# Application runners
api: ## Run the API server
	uv run python run_api.py

cli: ## Run the CLI (requires file argument: make cli FILE=path/to/file.txt)
	uv run python cli.py $(FILE)

# Docker targets
docker-build: ## Build Docker image
	docker build -t berlinger-fridge-tag:latest .

docker-run: ## Run Docker container
	docker run -d --name berlinger-fridge-tag -p 8000:8000 berlinger-fridge-tag:latest

docker-run-interactive: ## Run Docker container interactively
	docker run -it --rm -p 8000:8000 berlinger-fridge-tag:latest

docker-stop: ## Stop Docker container
	docker stop berlinger-fridge-tag || true

docker-clean: ## Remove Docker container and image
	docker stop berlinger-fridge-tag || true
	docker rm berlinger-fridge-tag || true
	docker rmi berlinger-fridge-tag:latest || true

# Cleanup
clean: ## Clean up build artifacts and caches
	rm -rf .venv/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true

# CI targets
ci-test: lint fmt-check test ## Run all CI checks

# Development workflow
all: install lint fmt test ## Install, lint, format, and test