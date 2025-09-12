# LLMFLOW - Insights API

A FastAPI-based application for product insights, reviews, and job management with background workers.

## 🚀 Quick Start

### Prerequisites

- Docker 27.x+ 
- Docker Compose 2.x+
- Python 3.11+ (for local development)
- uv (Python package manager)

### Docker Setup (WSL/Ubuntu)

If you need to install Docker and Docker Compose:

```bash
# Install Docker
sudo apt update
sudo apt install -y docker.io

# Install Docker Compose (standalone)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group (optional, requires logout/login)
sudo usermod -aG docker $USER
```

### Development Environment

1. **Start the development environment:**
   ```bash
   make dev
   ```

2. **Access the services:**
   - **API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **pgAdmin**: http://localhost:8080 (admin@insights.com / admin)
   - **Redis Commander**: http://localhost:8081 (admin / admin)
   - **ARQ Monitor**: http://localhost:8082

3. **Stop the environment:**
   ```bash
   make down
   ```

## 📋 Available Commands

```bash
make help          # Show all available commands
make install       # Install Python dependencies
make dev           # Start development environment
make down          # Stop all services
make logs          # Show all service logs
make logs-api      # Show API logs only
make logs-worker   # Show worker logs only
make shell         # Open shell in API container
make clean         # Clean up containers and volumes
make test          # Run tests
make format        # Format code
make lint          # Run linting
```

## 🏗️ Architecture

- **FastAPI** - Main API application
- **ARQ** - Background job processing with Redis
- **PostgreSQL** - Primary database
- **Redis** - Caching and job queue
- **WebSockets** - Real-time communication

## 🗄️ Database Operations

```bash
make db-migrate    # Generate new migration
make db-upgrade    # Apply migrations
make db-downgrade  # Downgrade migrations
```

## 🧪 Testing

```bash
make test          # Run all tests
make test-cov      # Run tests with coverage
```

## 📝 Notes

- Uses Docker Compose v2 syntax
- Tested with Docker 27.5.1 and Docker Compose 2.39.2
- Built with uv for fast Python dependency management
- Supports both `docker-compose` and `docker compose` commands

## 🔧 Troubleshooting

**Docker Compose not found?**
- Use the full path: `/usr/local/bin/docker-compose`
- Or use the newer syntax: `docker compose`

**Permission issues?**
- Make sure you're in the docker group: `sudo usermod -aG docker $USER`
- Logout and login again for group changes to take effect