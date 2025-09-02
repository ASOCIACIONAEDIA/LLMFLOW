# Use Python 3.11 slim image as base
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy uv configuration
COPY pyproject.toml uv.lock* README.md ./

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
COPY --chown=app:app . .

# Create logs directory
RUN mkdir -p logs && chown app:app logs

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

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
    which uvicorn && which arq

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment
ENV PYTHONPATH=/app
ENV ENVIRONMENT=development

# Command for development - use full path to be safe
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
