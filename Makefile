# Makefile for DepScan

.PHONY: help install install-dev test test-unit clean build frontend backend start-dev start-docker-dev stop-docker-dev restart-docker-dev start-staging stop-staging restart-staging lint format docker-dev docker-staging logs-dev logs-dev-frontend logs-dev-backend logs-staging logs-staging-frontend logs-staging-backend logs-staging-nginx status-dev status-staging health-check-dev health-check-staging setup-dev setup-staging cache-stats cache-clear cache-cleanup cache-demo

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
	@echo "  start-dev             Start development servers (manual)"
	@echo "  start-docker-dev      Start development with Docker"
	@echo "  stop-docker-dev       Stop Docker development environment"
	@echo "  restart-docker-dev    Restart Docker development environment"
	@echo ""
	@echo "🏭 Staging:"
	@echo "  start-staging         Start staging environment"
	@echo "  stop-staging          Stop staging environment"
	@echo "  restart-staging       Restart staging environment"
	@echo ""
	@echo "📊 Monitoring & Status:"
	@echo "  status-dev            Show development environment status"
	@echo "  status-staging        Show staging environment status"
	@echo "  health-check-dev      Health check development services"
	@echo "  health-check-staging  Health check staging services"
	@echo "  logs-dev              View all development logs"
	@echo "  logs-dev-frontend     View development frontend logs"
	@echo "  logs-dev-backend      View development backend logs"
	@echo "  logs-staging          View all staging logs"
	@echo "  logs-staging-frontend View staging frontend logs"
	@echo "  logs-staging-backend  View staging backend logs"
	@echo "  logs-staging-nginx    View staging nginx logs"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint          Run linting"
	@echo "  format        Format code"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-dev      Build development Docker images"
	@echo "  docker-staging  Build staging Docker images"
	@echo ""
	@echo "⚙️  Environment Setup:"
	@echo "  setup-dev       Set up development environment files"
	@echo "  setup-staging   Set up staging environment files"
	@echo ""
	@echo "🗄️  Cache Management:"
	@echo "  cache-stats     Show npm version cache statistics"
	@echo "  cache-clear     Clear all cached npm version data"
	@echo "  cache-cleanup   Remove expired cache entries only"
	@echo "  cache-demo      Run cache management demonstration"
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
	@echo "Adminer (database): http://localhost:8080"
	@echo ""
	@echo "View logs: make logs-dev"
	@echo "View frontend logs: make logs-dev-frontend"
	@echo "View backend logs: make logs-dev-backend"
	@echo "Stop: make stop-docker-dev"

stop-docker-dev:
	@echo "🛑 Stopping Docker development environment..."
	docker-compose -f docker-compose.dev.yml down
	@echo "✅ Development environment stopped!"

restart-docker-dev:
	@echo "🔄 Restarting Docker development environment..."
	docker-compose -f docker-compose.dev.yml restart
	@echo "✅ Development environment restarted!"

logs-dev:
	docker-compose -f docker-compose.dev.yml logs -f

logs-dev-frontend:
	docker-compose -f docker-compose.dev.yml logs -f frontend

logs-dev-backend:
	docker-compose -f docker-compose.dev.yml logs -f backend

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

# Cache management
cache-stats:
	@echo "📊 Getting cache statistics..."
	curl -s http://localhost:8000/admin/cache/stats | python -m json.tool

cache-clear:
	@echo "🧹 Clearing npm version cache..."
	curl -s -X POST http://localhost:8000/admin/cache/clear | python -m json.tool

cache-cleanup:
	@echo "🧽 Cleaning up expired cache entries..."
	curl -s -X POST http://localhost:8000/admin/cache/cleanup | python -m json.tool

cache-demo:
	@echo "🎬 Running cache management demo..."
	cd backend && python examples/cache_management_demo.py

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
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Nginx proxy: http://localhost:80"
	@echo ""
	@echo "View logs: make logs-staging"
	@echo "View frontend logs: make logs-staging-frontend"
	@echo "View backend logs: make logs-staging-backend"
	@echo "Stop: make stop-staging"

stop-staging:
	@echo "🛑 Stopping staging environment..."
	docker-compose -f docker-compose.staging.yml down
	@echo "✅ Staging environment stopped!"

restart-staging:
	@echo "🔄 Restarting staging environment..."
	docker-compose -f docker-compose.staging.yml restart
	@echo "✅ Staging environment restarted!"

logs-staging:
	docker-compose -f docker-compose.staging.yml logs -f

logs-staging-frontend:
	docker-compose -f docker-compose.staging.yml logs -f frontend

logs-staging-backend:
	docker-compose -f docker-compose.staging.yml logs -f dep-scanner

logs-staging-nginx:
	docker-compose -f docker-compose.staging.yml logs -f nginx

# Status and health commands
status-dev:
	@echo "🔍 Development environment status:"
	@docker-compose -f docker-compose.dev.yml ps

status-staging:
	@echo "🔍 Staging environment status:"
	@docker-compose -f docker-compose.staging.yml ps

health-check-dev:
	@echo "🏥 Checking development environment health..."
	@curl -s http://localhost:8000/health || echo "❌ Backend health check failed"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend is running" || echo "❌ Frontend health check failed"

health-check-staging:
	@echo "🏥 Checking staging environment health..."
	@curl -s http://localhost:8000/health || echo "❌ Backend health check failed"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend is running" || echo "❌ Frontend health check failed"
	@curl -s http://localhost:80/health || echo "❌ Nginx proxy health check failed"

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

setup-staging:
	@echo "🛠️  Setting up staging environment..."
	cp .env.example .env.staging
	cp frontend/.env.example frontend/.env.staging
	@echo "✅ Environment files created! Please review and customize them."
	@echo ""
	@echo "Next steps:"
	@echo "1. Review .env.staging and frontend/.env.staging"
	@echo "2. Run 'make docker-staging' to build staging images"
	@echo "3. Run 'make start-staging' to start staging environment"