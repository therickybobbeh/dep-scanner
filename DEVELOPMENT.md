# 🛠️ DepScan Development Guide

This guide provides detailed instructions for setting up and working with the DepScan development environment.

## 🚀 Quick Start

### Automated Setup (Recommended)

The fastest way to get started is with our automated setup scripts:

```bash
# macOS/Linux
./setup-dev.sh

# Windows
setup-dev.bat
```

These scripts will:
- ✅ Check system requirements (Python 3.11+, Node.js 18+, npm)
- ✅ Set up environment files
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Show next steps

### Manual Setup

If you prefer manual setup or need to troubleshoot:

```bash
# 1. Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Frontend setup
cd ../frontend
npm install

# 3. Environment files
cp .env.development .env
cp frontend/.env.development frontend/.env

# 4. Create directories
mkdir -p data logs backend/data backend/logs
```

## 🐳 Development Options

### Option 1: Docker Development (Recommended)

Best for consistent environments and easy setup:

```bash
# Start development environment
make start-docker-dev

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop environment
make stop-docker-dev
```

**Benefits:**
- ✅ Consistent environment across all machines
- ✅ Automatic hot reload for both frontend and backend
- ✅ No need to install Python/Node.js locally
- ✅ Easy cleanup

**Access Points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Option 2: Manual Development

For developers who prefer direct control:

```bash
# Terminal 1 - Backend
cd backend
source .venv/bin/activate
python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend  
cd frontend
npm run dev
```

**Benefits:**
- ✅ Direct access to Python environment
- ✅ Easier debugging and profiling
- ✅ More control over processes
- ✅ Better IDE integration

## 🎯 VS Code Integration

For the best development experience, use our VS Code workspace:

```bash
code depscan.code-workspace
```

### Pre-configured Features:

**🐍 Python Development:**
- Virtual environment auto-activation
- Flake8 and MyPy linting
- Black code formatting
- Pytest integration
- Debug configurations

**⚛️ Frontend Development:**
- TypeScript support
- ESLint integration
- Prettier formatting
- React debugging

**🧰 Development Tasks:**
- Start/stop Docker development
- Run tests and linting
- Build and deployment tasks
- Terminal profiles for backend/frontend

### Recommended Extensions:

The workspace automatically suggests these extensions:
- **Python**: `ms-python.python`
- **TypeScript**: `ms-vscode.vscode-typescript-next`
- **Docker**: `ms-azuretools.vscode-docker`
- **Prettier**: `esbenp.prettier-vscode`
- **GitLens**: `eamodio.gitlens`

## 📁 Project Structure

```
DepScan/
├── 🐍 backend/                 # Python FastAPI backend
│   ├── web/                    # Web API modules
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── api/               # API route handlers
│   │   ├── core/              # Business logic
│   │   ├── models/            # Data models
│   │   └── utils/             # Utilities
│   ├── cli.py                 # Command-line interface
│   ├── requirements.txt       # Python dependencies
│   ├── tests/                 # Backend tests
│   └── .venv/                 # Virtual environment
├── ⚛️ frontend/               # React TypeScript frontend
│   ├── src/                   # Source code
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── types/             # TypeScript definitions
│   │   ├── utils/             # Utility functions
│   │   └── hooks/             # Custom React hooks
│   ├── public/                # Static assets
│   ├── package.json           # Node.js dependencies
│   └── node_modules/          # Dependencies
├── 🐳 Docker & Compose Files   # Container configurations
│   ├── Dockerfile.dev         # Development backend image
│   ├── Dockerfile.aws         # Production backend image
│   ├── docker-compose.dev.yml # Development environment
│   └── docker-compose.staging.yml # Staging environment
├── 📄 Environment Configs     # Configuration files
│   ├── .env.example           # Template
│   ├── .env.development       # Development settings
│   ├── .env.staging           # Staging settings
│   └── .env.production        # Production settings
├── 🛠️ Development Tools       # Developer experience
│   ├── .vscode/               # VS Code configuration
│   ├── Makefile               # Build automation
│   ├── setup-dev.sh           # Setup script (Unix)
│   └── setup-dev.bat          # Setup script (Windows)
└── 📚 Documentation           # Project documentation
    ├── README.md              # Main documentation
    └── DEVELOPMENT.md         # This file
```

## 🧪 Testing

### Backend Tests

```bash
# Run all backend tests
cd backend && pytest tests/ -v

# Run with coverage
cd backend && pytest tests/ -v --cov=web --cov-report=html

# Run specific test file
cd backend && pytest tests/test_parsers.py -v

# Run with debugger on failures
cd backend && pytest tests/ -v --pdb
```

### Frontend Tests

```bash
# Run frontend tests
cd frontend && npm test

# Run tests in watch mode
cd frontend && npm run test:watch

# Run tests with coverage
cd frontend && npm run test:coverage
```

### Integration Tests

```bash
# Full integration test using Make
make test

# Test the CLI directly
cd backend && python cli.py scan ../sample-project
```

## 🔍 Code Quality

### Linting

```bash
# Backend linting
make lint-backend
# Or manually:
cd backend && flake8 web/ cli.py
cd backend && mypy web/ cli.py --ignore-missing-imports

# Frontend linting
make lint-frontend
# Or manually:
cd frontend && npm run lint
```

### Code Formatting

```bash
# Format all code
make format

# Backend formatting
cd backend && black web/ cli.py tests/
cd backend && isort web/ cli.py tests/

# Frontend formatting
cd frontend && npm run format
```

## 🔧 Environment Configuration

### Backend Environment Variables

Create `.env` files for different environments:

```bash
# Development (.env.development)
ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CACHE_DB_PATH=./data/dev_osv_cache.db
CACHE_TTL_HOURS=2

# Staging (.env.staging)
ENV=staging
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
CACHE_TTL_HOURS=12
```

### Frontend Environment Variables

```bash
# Development (frontend/.env.development)
VITE_API_URL=http://localhost:8000
VITE_DEBUG_MODE=true

# Staging (frontend/.env.staging - if needed)
VITE_API_URL=http://localhost:8000
VITE_DEBUG_MODE=false
```

## 🚀 Deployment

### Development Deployment

```bash
# Start development environment
make start-docker-dev

# Or with docker-compose directly
docker-compose -f docker-compose.dev.yml up --build
```

### Staging Deployment

```bash
# Build and start staging environment
make start-staging

# Or manually with docker-compose
docker-compose -f docker-compose.staging.yml up --build

# Stop staging environment
make stop-staging
```

## 🐛 Debugging

### Backend Debugging

**VS Code Debugging:**
1. Open VS Code workspace: `code depscan.code-workspace`
2. Set breakpoints in Python code
3. Press F5 or select "🐍 Debug Backend API" configuration
4. Debug with full breakpoint support

**Manual Debugging:**
```bash
cd backend
source .venv/bin/activate
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn web.main:app --reload
```

### Frontend Debugging

- Use browser DevTools for React debugging
- React DevTools extension recommended
- VS Code debugging for TypeScript files

### CLI Debugging

```bash
cd backend
source .venv/bin/activate
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client cli.py scan /path/to/project
```

## 📦 Dependencies

### Adding Backend Dependencies

```bash
cd backend
source .venv/bin/activate
pip install new-package
pip freeze > requirements.txt
```

### Adding Frontend Dependencies

```bash
cd frontend
npm install new-package
# Dependencies automatically saved to package.json
```

## 🚨 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
# Kill processes using ports 3000 or 8000
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

**Docker Issues:**
```bash
# Clean up Docker
docker system prune -a
docker-compose -f docker-compose.dev.yml down --volumes
```

**Permission Issues (Linux/macOS):**
```bash
# Fix ownership
sudo chown -R $USER:$USER .
```

**Virtual Environment Issues:**
```bash
# Recreate virtual environment
cd backend
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Getting Help

1. Check the [README.md](README.md) for basic usage
2. Review this development guide
3. Check existing issues in the repository
4. Use VS Code workspace for better development experience
5. Enable debug logging: `LOG_LEVEL=DEBUG` in your `.env` file

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** using the development environment
4. **Add tests** for your changes
5. **Run quality checks**: `make lint && make test`
6. **Commit your changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Development Workflow

```bash
# 1. Set up development environment
./setup-dev.sh

# 2. Start development
make start-docker-dev

# 3. Make changes and test
make test
make lint

# 4. Format code
make format

# 5. Commit changes
git add .
git commit -m "Description of changes"
```

---

Happy coding! 🚀