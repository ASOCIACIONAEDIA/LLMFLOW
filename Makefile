# Makefile for Insights API

.PHONY: help dev prod test clean build up down logs shell db-migrate db-upgrade db-downgrade format lint
.PHONY: test-unit test-integration test-cov test-debug test-e2e ci-test test-setup
.PHONY: install-local format-local lint-local test-local

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "=== DEVELOPMENT ==="
	@echo "  dev             - Start development environment (Docker)"
	@echo "  prod            - Start production environment (Docker)"
	@echo "  shell           - Open shell in API container"
	@echo "  logs            - Show logs from all services"
	@echo ""
	@echo "=== DOCKER OPERATIONS ==="
	@echo "  build           - Build Docker images"
	@echo "  up              - Start all services"
	@echo "  down            - Stop all services"
	@echo "  clean           - Clean up containers and volumes"
	@echo ""
	@echo "=== DATABASE ==="
	@echo "  db-migrate      - Generate new migration (in Docker)"
	@echo "  db-upgrade      - Apply migrations (in Docker)"
	@echo "  db-downgrade    - Downgrade migrations (in Docker)"
	@echo ""
	@echo "=== TESTING (Docker-based) ==="
	@echo "  test            - Run all tests in Docker"
	@echo "  test-unit       - Run unit tests in Docker"
	@echo "  test-integration- Run integration tests in Docker"
	@echo "  test-e2e        - Run end-to-end tests in Docker"
	@echo "  test-cov        - Run tests with coverage in Docker"
	@echo "  test-debug      - Run tests with debugging in Docker"
	@echo "  ci-test         - Run complete CI test suite in Docker"
	@echo ""
	@echo "=== CODE QUALITY (Docker-based) ==="
	@echo "  format          - Format code with black and isort (in Docker)"
	@echo "  lint            - Run linting checks (in Docker)"
	@echo ""
	@echo "=== LOCAL DEVELOPMENT (Optional) ==="
	@echo "  install-local   - Install dependencies locally with uv"
	@echo "  format-local    - Format code locally"
	@echo "  lint-local      - Run linting checks locally"
	@echo "  test-local      - Run tests locally (requires local setup)"

# Development setup
dev: 
	@echo "Starting development environment..."
	DOCKER_BUILDKIT=0 docker-compose up --build -d
	@echo ""
	@echo "🚀 Development environment is running!"
	@echo ""
	@echo "Services available at:"
	@echo "  • API: http://localhost:8000"
	@echo "  • API Docs: http://localhost:8000/docs"
	@echo "  • pgAdmin: http://localhost:8080 (admin@insights.com / admin)"
	@echo "  • Redis Commander: http://localhost:8081 (admin / admin)"
	@echo "  • ARQ Monitor: http://localhost:8082/arq/ui"
	@echo ""
	@echo "💡 Run 'make test' to run tests in Docker!"
	@echo "💡 Run 'make shell' to open a shell in the API container!"

# Local development setup (optional)
install-local:
	@echo "📦 Installing dependencies locally with uv..."
	uv sync
	uv lock
	@echo ""
	@echo "✅ Local dependencies installed!"
	@echo "💡 You can now use format-local, lint-local, and test-local commands"

prod:
	@echo "Starting production environment..."
	BUILD_TARGET=production docker-compose up --build -d

# Docker operations
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	docker-compose down -v --remove-orphans
	docker system prune -a -f

logs:
	docker-compose logs -f

shell:
	docker-compose exec api bash

# Database operations
db-migrate:
	@read -p "Enter migration message: " message; \
	docker-compose exec api alembic revision --autogenerate -m "$$message"

db-upgrade:
	docker-compose exec api alembic upgrade head

db-downgrade:
	@read -p "Enter target revision (or -1 for previous): " revision; \
	docker-compose exec api alembic downgrade $$revision

# === DOCKER-FIRST TESTING ===

test-setup:
	@echo "🔧 Setting up test environment..."
	docker-compose up -d --wait
	@echo "✅ Test environment ready!"

test:
	@echo "🧪 Running all tests in Docker..."
	@echo "Starting services with dependency health checks..."
	docker-compose up -d --wait
	@echo "✅ All services are ready!"
	@echo "Running all tests..."
	docker-compose exec -e DOCKER_ENV=true api pytest tests/ -v

test-unit:
	@echo "🔬 Running unit tests in Docker..."
	docker-compose up -d --wait
	docker-compose exec -e DOCKER_ENV=true api pytest tests/unit/ -v

test-integration:
	@echo "🔗 Running integration tests in Docker..."
	docker-compose up -d --wait
	docker-compose exec -e DOCKER_ENV=true api pytest tests/integration/ -v

test-e2e:
	@echo "🌐 Running end-to-end tests in Docker..."
	docker-compose up -d --wait
	docker-compose exec -e DOCKER_ENV=true api pytest tests/e2e/ -v

test-cov:
	@echo "📊 Running tests with coverage in Docker..."
	docker-compose up -d --wait
	docker-compose exec -e DOCKER_ENV=true api pytest --cov=app --cov-report=html --cov-report=term-missing

test-debug:
	@echo "🐛 Running tests with debugging in Docker..."
	docker-compose up -d --wait
	docker-compose exec -e DOCKER_ENV=true api pytest tests/ -v -s --pdb

# Docker-based code quality
format:
	@echo "🎨 Formatting code in Docker..."
	docker-compose exec api black .
	docker-compose exec api isort .

lint:
	@echo "🔍 Running linting checks in Docker..."
	docker-compose exec api flake8 .
	docker-compose exec api mypy app/

# CI pipeline (Docker-based)
ci-test:
	@echo "🚀 Running CI test suite in Docker..."
	$(MAKE) test-setup
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) test-e2e
	$(MAKE) test-cov
	@echo "✅ CI test suite completed successfully!"

# Quick development check
check:
	@echo "⚡ Running quick checks in Docker..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test-unit
	@echo "✅ Quick checks completed!"

# === OPTIONAL LOCAL DEVELOPMENT ===

format-local:
	@echo "🎨 Formatting code locally..."
	uv run black .
	uv run isort .

lint-local:
	@echo "🔍 Running linting checks locally..."
	uv run flake8 .
	uv run mypy app/

test-local:
	@echo "🧪 Running tests locally..."
	@echo "⚠️  Warning: This requires local Python environment setup"
	uv run pytest tests/ -v