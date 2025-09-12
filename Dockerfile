# Use Python 3.11 slim image as base
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy uv configuration
COPY insights-api/pyproject.toml insights-api/uv.lock* insights-api/README.md ./

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Debug: List what's in the virtual environment
RUN echo "=== DEBUG: Base stage .venv/bin/ ===" && \
    ls -la /app/.venv/bin/ && \
    echo "=== Looking for uvicorn and arq in base ===" && \
    (ls -la /app/.venv/bin/ | grep -E "(uvicorn|arq)" || echo "uvicorn or arq not found in base stage")

# Production stage
FROM python:3.11-slim as production

# Install system dependencies for production
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy virtual environment from base stage
COPY --from=base /app/.venv /app/.venv

# Make sure to use venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --chown=app:app insights-api/ ./

# Create necessary directories
RUN mkdir -p logs htmlcov reports && chown -R app:app logs htmlcov reports

# Create alembic directory if it doesn't exist
RUN mkdir -p alembic/versions && chown -R app:app alembic

# Switch to non-root user
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check - enhanced for user management endpoints
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || \
        curl -f http://localhost:8000/ || exit 1

# Default command (can be overridden in docker-compose)
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

# Set PATH early
ENV PATH="/app/.venv/bin:$PATH"

# Install dev dependencies
RUN uv sync --frozen

# Debug: List what's in the virtual environment after dev install
RUN echo "=== DEBUG: Development stage .venv/bin/ ===" && \
    ls -la /app/.venv/bin/ && \
    echo "=== Looking for uvicorn and arq in dev ===" && \
    (ls -la /app/.venv/bin/ | grep -E "(uvicorn|arq)" || echo "uvicorn or arq not found in dev stage") && \
    echo "=== Checking if arq is importable ===" && \
    /app/.venv/bin/python -c "import arq; print('arq imported successfully')" || echo "arq import failed" && \
    echo "=== Testing PATH ===" && \
    which uvicorn && which arq && \
    echo "=== Checking pytest and testing tools ===" && \
    (ls -la /app/.venv/bin/ | grep -E "(pytest|black|isort|mypy)" || echo "testing tools not found")

# Copy application code
COPY insights-api/ ./

# Create necessary directories for development
RUN mkdir -p logs htmlcov reports alembic/versions

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=development

# Command for development - use full path to be safe
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Testing stage - NEW for our enhanced testing suite
FROM development as testing

# Set environment for testing
ENV ENVIRONMENT=test
ENV PYTHONPATH=/app

# Copy test configuration files
COPY pytest.ini ./
COPY .coveragerc ./

# Ensure test directories exist
RUN mkdir -p tests/unit tests/integration tests/e2e tests/utils tests/fixtures

# Default command for testing
CMD ["/app/.venv/bin/pytest", "tests/", "-v", "--cov=app", "--cov-report=html", "--cov-report=term-missing"]
