# Makefile for Insights API

.PHONY: help install dev prod test clean build up down logs shell db-migrate db-upgrade db-downgrade format lint logs-redis-commander
.PHONY: test-unit test-integration test-e2e test-auth test-user-management test-fast test-verbose
.PHONY: test-cov-full test-docker test-docker-quick test-with-db test-setup test-cleanup
.PHONY: ci-test pre-commit test-debug test-watch test-security

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "=== DEVELOPMENT ==="
	@echo "  install         - Install dependencies with uv"
	@echo "  dev             - Start development environment"
	@echo "  prod            - Start production environment"
	@echo "  format          - Format code with black and isort"
	@echo "  lint            - Run linting checks"
	@echo ""
	@echo "=== DOCKER OPERATIONS ==="
	@echo "  build           - Build Docker images"
	@echo "  up              - Start all services"
	@echo "  down            - Stop all services"
	@echo "  clean           - Clean up containers and volumes"
	@echo "  logs            - Show logs"
	@echo "  shell           - Open shell in API container"
	@echo "  status          - Show service status"
	@echo "  monitor         - Show monitoring URLs"
	@echo ""
	@echo "=== DATABASE ==="
	@echo "  db-migrate      - Generate new migration"
	@echo "  db-upgrade      - Apply migrations"
	@echo "  db-downgrade    - Downgrade migrations"
	@echo ""
	@echo "=== TESTING ==="
	@echo "  test            - Run all tests"
	@echo "  test-fast       - Run unit tests only (quick feedback)"
	@echo "  test-unit       - Run unit tests"
	@echo "  test-integration- Run integration tests"
	@echo "  test-e2e        - Run end-to-end tests"
	@echo "  test-auth       - Run authentication-specific tests"
	@echo "  test-user-mgmt  - Run user management tests"
	@echo "  test-security   - Run security-focused tests"
	@echo "  test-cov        - Run tests with coverage report"
	@echo "  test-cov-full   - Run tests with comprehensive coverage"
	@echo "  test-docker     - Run tests in Docker environment"
	@echo "  test-with-db    - Run tests with real database"
	@echo "  test-debug      - Run tests with debugging enabled"
	@echo ""
	@echo "=== CI/CD ==="
	@echo "  ci-test         - Run full CI test suite"
	@echo "  pre-commit      - Run pre-commit checks"
	@echo "  check           - Run format, lint, and tests"

# Development setup
install:
	uv sync
	uv lock

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
	@echo "  • ARQ Monitor: http://localhost:8082"
	@echo ""
	@echo "Use 'make logs' to see logs or 'make down' to stop"

prod:
	@echo "Starting production environment..."
	BUILD_TARGET=production docker-compose up --build -d
	@echo "Production environment started!"

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
	docker volume prune -f

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f worker

logs-redis-commander:
	docker-compose logs -f redis-commander

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

# === ENHANCED TESTING SUITE ===

# Basic testing commands
test:
	@echo "🧪 Running all tests..."
	uv run pytest tests/ -v

test-fast:
	@echo "⚡ Running fast unit tests for quick feedback..."
	uv run pytest tests/unit/ --maxfail=5 -x -q

test-verbose:
	@echo "📝 Running tests with verbose output..."
	uv run pytest tests/ -v -s

# Test by category
test-unit:
	@echo "🔬 Running unit tests..."
	uv run pytest tests/unit/ -v

test-integration:
	@echo "🔗 Running integration tests..."
	uv run pytest tests/integration/ -v

test-e2e:
	@echo "🌐 Running end-to-end tests..."
	uv run pytest tests/e2e/ -v

# Feature-specific testing
test-auth:
	@echo "🔐 Running authentication tests..."
	uv run pytest tests/unit/api/v1/test_auth.py \
	              tests/unit/services/test_auth_services.py \
	              tests/integration/test_complete_auth_flow.py -v

test-user-mgmt:
	@echo "👥 Running user management tests..."
	uv run pytest tests/unit/api/v1/test_users.py \
	              tests/unit/services/test_user_service.py \
	              tests/unit/repositories/test_user_repo.py -v

test-security:
	@echo "🛡️ Running security-focused tests..."
	uv run pytest tests/unit/core/test_security.py \
	              tests/unit/api/v1/test_auth.py \
	              -k "security or auth or password or token" -v

# Coverage testing
test-cov:
	@echo "📊 Running tests with basic coverage..."
	uv run pytest --cov=app --cov-report=html --cov-report=term-missing

test-cov-full:
	@echo "📈 Running comprehensive coverage analysis..."
	uv run pytest --cov=app \
	              --cov-report=html \
	              --cov-report=term-missing \
	              --cov-report=xml \
	              --cov-fail-under=80 \
	              --cov-branch

test-cov-auth:
	@echo "🔐📊 Running auth-specific coverage..."
	uv run pytest tests/unit/api/v1/test_auth.py \
	              tests/unit/services/test_auth_services.py \
	              --cov=app.api.v1.auth \
	              --cov=app.services.auth_services \
	              --cov-report=html \
	              --cov-report=term-missing

# Docker-based testing
test-docker:
	@echo "🐳 Running tests in Docker environment..."
	@if [ ! -f docker-compose.test.yml ]; then \
		echo "❌ docker-compose.test.yml not found!"; \
		echo "Please create it manually or run 'make _create-test-compose'"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
	docker-compose -f docker-compose.test.yml down

test-docker-quick:
	@echo "🐳⚡ Running quick tests in running Docker environment..."
	docker-compose exec api pytest tests/unit/ -v

test-docker-integration:
	@echo "🐳🔗 Running integration tests in Docker..."
	docker-compose exec api pytest tests/integration/ -v

# Database testing
test-with-db:
	@echo "🗄️ Running tests with real database..."
	$(MAKE) test-setup
	@echo "Database ready, running tests..."
	uv run pytest tests/ -v
	$(MAKE) test-cleanup

test-db-migration:
	@echo "🗄️🔄 Testing database migrations..."
	docker-compose exec api alembic upgrade head
	docker-compose exec api alembic downgrade base
	docker-compose exec api alembic upgrade head
	@echo "Migration tests completed!"

# Test environment management
test-setup:
	@echo "🔧 Setting up test environment..."
	docker-compose up -d postgres redis
	@echo "Waiting for services to be ready..."
	@sleep 10
	$(MAKE) db-upgrade
	@echo "Test environment ready!"

test-cleanup:
	@echo "🧹 Cleaning up test environment..."
	-docker-compose exec postgres psql -U insights_user -d insights -c "TRUNCATE users, organizations, email_verifications, two_factor_codes, refresh_tokens CASCADE;" 2>/dev/null || true
	-docker-compose exec redis redis-cli FLUSHDB 2>/dev/null || true
	@echo "Test environment cleaned!"

test-reset:
	@echo "🔄 Resetting test environment..."
	$(MAKE) test-cleanup
	$(MAKE) test-setup

# Development and debugging
test-debug:
	@echo "🐛 Running tests with debugging enabled..."
	uv run pytest tests/ -v -s --pdb

test-watch:
	@echo "👀 Running tests in watch mode..."
	@if command -v ptw >/dev/null 2>&1; then \
		uv run ptw tests/ app/ -- --testmon; \
	else \
		echo "Installing pytest-watch..."; \
		uv add pytest-watch pytest-testmon --dev; \
		uv run ptw tests/ app/ -- --testmon; \
	fi

test-failed:
	@echo "🔍 Re-running only failed tests..."
	uv run pytest --lf -v

test-profile:
	@echo "⏱️ Running tests with profiling..."
	uv run pytest tests/ --profile-svg

# CI/CD pipeline targets
ci-test:
	@echo "🚀 Running full CI test suite..."
	@echo "Step 1: Code formatting..."
	$(MAKE) format
	@echo "Step 2: Linting..."
	$(MAKE) lint
	@echo "Step 3: Unit tests..."
	$(MAKE) test-unit
	@echo "Step 4: Integration tests..."
	$(MAKE) test-integration
	@echo "Step 5: Coverage analysis..."
	$(MAKE) test-cov-full
	@echo "✅ All CI tests passed!"

ci-test-fast:
	@echo "🚀⚡ Running fast CI tests..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test-fast

pre-commit:
	@echo "🔍 Running pre-commit checks..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test-unit
	@echo "✅ Pre-commit checks passed!"

# Development tools
format:
	@echo "🎨 Formatting code..."
	uv run black .
	uv run isort .

lint:
	@echo "🔍 Running linting checks..."
	uv run flake8 .
	uv run mypy app/

# Quick checks
check: format lint test-fast
	@echo "✅ All quick checks passed!"

check-full: format lint test
	@echo "✅ All comprehensive checks passed!"

# Monitor services
monitor:
	@echo "📊 Monitoring URLs:"
	@echo "  • pgAdmin: http://localhost:8080"
	@echo "  • Redis Commander: http://localhost:8081"
	@echo "  • ARQ Monitor: http://localhost:8082"
	@echo "  • API Health: http://localhost:8000/"
	@echo "  • API Docs: http://localhost:8000/docs"

# Show service status
status:
	docker-compose ps

# Reset everything
reset: clean
	docker volume prune -f
	docker-compose up --build -d