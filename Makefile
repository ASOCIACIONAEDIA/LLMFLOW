# Makefile for Insights API

.PHONY: help install dev prod test clean build up down logs shell db-migrate db-upgrade db-downgrade format lint

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies with uv"
	@echo "  dev         - Start development environment"
	@echo "  prod        - Start production environment"
	@echo "  test        - Run tests"
	@echo "  clean       - Clean up containers and volumes"
	@echo "  build       - Build Docker images"
	@echo "  up          - Start all services"
	@echo "  down        - Stop all services"
	@echo "  logs        - Show logs"
	@echo "  shell       - Open shell in API container"
	@echo "  db-migrate  - Generate new migration"
	@echo "  db-upgrade  - Apply migrations"
	@echo "  db-downgrade - Downgrade migrations"
	@echo "  format      - Format code with black and isort"
	@echo "  lint        - Run linting checks"

# Development setup
install:
	uv sync

dev: 
	@echo "Starting development environment..."
	docker-compose up --build -d
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

# Development tools
test:
	uv run pytest

test-cov:
	uv run pytest --cov=app --cov-report=html

format:
	uv run black .
	uv run isort .

lint:
	uv run flake8 .
	uv run mypy app/

# Quick checks
check: format lint test

# Monitor services
monitor:
	@echo "Monitoring URLs:"
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