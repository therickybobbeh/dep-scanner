# Makefile for DepScan

.PHONY: help install install-dev test test-unit test-integration clean build frontend backend start-dev lint format

help:
	@echo "Available commands:"
	@echo "  help          Show this help message"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build both frontend and backend"
	@echo "  frontend      Build frontend only"
	@echo "  backend       Install backend dependencies"
	@echo "  start-dev     Start development servers"
	@echo "  lint          Run linting"
	@echo "  format        Format code"

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
	cd backend && python -m pytest tests/unit/ -v

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
	@echo "Start backend: cd backend && python -m uvicorn app.main:app --reload"
	@echo "Start frontend: cd frontend && npm run dev"

lint:
	@echo "🔍 Running linters..."
	cd backend && python -m flake8 app/ cli.py
	cd backend && python -m mypy app/ cli.py --ignore-missing-imports
	cd frontend && npm run lint

format:
	@echo "🎨 Formatting code..."
	cd backend && python -m black app/ cli.py tests/
	cd backend && python -m isort app/ cli.py tests/

# CLI shortcuts
cli-help:
	cd backend && python cli.py --help

cli-scan:
	@echo "Usage: make cli-scan ARGS='path/to/project'"
	cd backend && python cli.py scan $(ARGS)

# Docker commands (future)
docker-build:
	docker build -t depscan:latest .

docker-run:
	docker run -p 8000:8000 depscan:latest