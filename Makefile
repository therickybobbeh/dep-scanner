# Makefile for DepScan

.PHONY: help install install-dev test test-unit test-integration clean build frontend backend start-dev start-docker-dev stop-docker-dev start-staging stop-staging lint format docker-dev docker-staging

help:
	@echo "🔧 DepScan Development Commands"
	@echo ""
	@echo "📦 Installation:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo ""
	@echo "🏗️  Building:"
	@echo "  build         Build both frontend and backend"
	@echo "  frontend      Build frontend only"
	@echo "  backend       Install backend dependencies"
	@echo ""
	@echo "🚀 Development:"
	@echo "  start-dev     Start development servers (manual)"
	@echo "  start-docker-dev Start development with Docker"
	@echo "  stop-docker-dev  Stop Docker development environment"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint          Run linting"
	@echo "  format        Format code"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-dev      Build development Docker images"
	@echo "  docker-staging  Build staging Docker images"
	@echo "  start-staging   Start staging environment"
	@echo "  stop-staging    Stop staging environment"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean         Clean build artifacts"

install: backend frontend
	@echo "✅ Installation complete"

install-dev: install
	cd backend && pip install -e ".[dev]"

backend:
	@echo "📦 Installing Python dependencies..."
	cd backend && python -m venv .venv
	cd backend && .venv/bin/pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

frontend:
	@echo "📦 Installing Node.js dependencies..."
	cd frontend && npm install
	@echo "🏗️ Building frontend..."
	cd frontend && npm run build
	@echo "✅ Frontend built successfully"

test: test-unit
	@echo "✅ All tests completed"

test-unit:
	@echo "🧪 Running unit tests..."
	cd backend && python -m pytest tests/ -v

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf backend/.venv
	rm -rf backend/build
	rm -rf backend/dist
	rm -rf backend/*.egg-info
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf frontend/build
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	@echo "✅ Clean complete"

build: frontend
	@echo "🏗️ Building project..."
	cd backend && pip install -e .
	@echo "✅ Build complete"

start-dev:
	@echo "🚀 Starting development servers..."
	@echo "Backend will be available at http://127.0.0.1:8000"
	@echo "Frontend will be available at http://127.0.0.1:3000"
	@echo ""
	@echo "Start backend: cd backend && python -m uvicorn web.main:app --reload"
	@echo "Start frontend: cd frontend && npm run dev"

start-docker-dev:
	@echo "🐳 Starting Docker development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Development environment started!"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@echo "View logs: docker-compose -f docker-compose.dev.yml logs -f"
	@echo "Stop: make stop-docker-dev"

stop-docker-dev:
	@echo "🛑 Stopping Docker development environment..."
	docker-compose -f docker-compose.dev.yml down
	@echo "✅ Development environment stopped!"

lint:
	@echo "🔍 Running linters..."
	cd backend && python -m flake8 web/ cli.py --ignore=E501,W503
	cd backend && python -m mypy web/ cli.py --ignore-missing-imports
	cd frontend && npm run lint

format:
	@echo "🎨 Formatting code..."
	cd backend && python -m black web/ cli.py tests/
	cd backend && python -m isort web/ cli.py tests/
	cd frontend && npm run format

# CLI shortcuts
cli-help:
	cd backend && python cli.py --help

cli-scan:
	@echo "Usage: make cli-scan ARGS='path/to/project'"
	cd backend && python cli.py scan $(ARGS)

# Docker commands
docker-dev:
	@echo "🐳 Building development Docker images..."
	docker-compose -f docker-compose.dev.yml build
	@echo "✅ Development images built!"

docker-staging:
	@echo "🐳 Building staging Docker images..."
	docker-compose -f docker-compose.staging.yml build
	@echo "✅ Staging images built!"

start-staging:
	@echo "🚀 Starting staging environment..."
	docker-compose -f docker-compose.staging.yml up -d
	@echo "✅ Staging environment started!"
	@echo "Access: http://localhost:8000"

stop-staging:
	@echo "🛑 Stopping staging environment..."
	docker-compose -f docker-compose.staging.yml down
	@echo "✅ Staging environment stopped!"

# Environment setup
setup-dev:
	@echo "🛠️  Setting up development environment..."
	cp .env.example .env.development
	cp frontend/.env.example frontend/.env.development
	@echo "✅ Environment files created! Please review and customize them."
	@echo ""
	@echo "Next steps:"
	@echo "1. Review .env.development and frontend/.env.development"
	@echo "2. Run 'make install-dev' to install dependencies"
	@echo "3. Run 'make start-docker-dev' to start development environment"