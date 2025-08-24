# 📦 Installation Guide

This guide covers multiple installation methods for DepScan, from quick Docker setup to local development installation.

## 🚀 Quick Start (Docker - Recommended)

The fastest way to get DepScan running is with Docker Compose:

### Prerequisites
- Docker 20.0+ and Docker Compose 2.0+
- Git (to clone repository)

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/yourusername/depscan.git
cd depscan

# 2. Start with Docker Compose
docker-compose up --build

# 3. Access interfaces
# Web Interface: http://localhost:8000
# CLI: docker exec -it depscan-backend python cli.py --help
```

### Docker Compose Services
- **Backend**: FastAPI server + CLI tool (Port 8000)  
- **Frontend**: React dashboard (served by backend)
- **Database**: SQLite cache (persistent volume)

---

## 🖥️ Local Installation

For development or when Docker isn't available:

### Prerequisites
- **Python 3.10+** (3.11+ recommended)
- **Node.js 18+** (for frontend)
- **Git** for cloning

### Backend Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/depscan.git
cd depscan

# 2. Create Python virtual environment
cd backend
python -m venv .venv

# 3. Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Verify CLI installation
python cli.py --help
```

### Frontend Setup (Optional)

The web interface is optional but provides a better user experience:

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node.js dependencies  
npm install

# 3. Build for production
npm run build

# 4. Development server (optional)
npm run dev  # Runs on http://localhost:5173
```

### Environment Configuration

Create a `.env` file in the backend directory for custom configuration:

```env
# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_RELOAD=false

# Cache Configuration
CACHE_TTL_HOURS=24
CACHE_CLEANUP_INTERVAL_HOURS=6

# OSV.dev API Configuration
OSV_API_URL=https://api.osv.dev
OSV_RATE_LIMIT_CALLS=100
OSV_RATE_LIMIT_PERIOD=60

# Frontend Configuration (for development)
VITE_API_BASE=http://127.0.0.1:8000
```

---

## 🧪 Verify Installation

### CLI Verification

```bash
# Test CLI help
python backend/cli.py --help

# Test version command
python backend/cli.py version

# Test scan on sample project
python backend/cli.py scan frontend/ --json test-report.json
```

Expected output:
```
✅ Found 47 dependencies (8 direct, 39 transitive)
🔍 Scanning for vulnerabilities...
📊 Found 2 vulnerabilities in 2 packages
📁 Report saved to: test-report.json
```

### Web Interface Verification

```bash
# Start web server
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Open browser to http://127.0.0.1:8000
# Should see DepScan dashboard
```

### Run Test Suite

```bash
# Run comprehensive tests
./run_tests.py

# Or run specific test categories
pytest tests/unit/parsers/ -v
pytest tests/integration/ -v
```

---

## 📊 Platform-Specific Instructions

### 🐧 Linux (Ubuntu/Debian)

```bash
# Update package manager
sudo apt update

# Install system dependencies
sudo apt install python3.11 python3.11-venv python3-pip nodejs npm git

# Create virtual environment with specific Python version
python3.11 -m venv .venv
```

### 🍎 macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node git

# Create virtual environment
python3.11 -m venv .venv
```

### 🪟 Windows

```powershell
# Install Python from python.org (3.10+)
# Install Node.js from nodejs.org (18+)
# Install Git from git-scm.com

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Continue with standard installation
pip install -r requirements.txt
```

---

## 🔧 Troubleshooting

### Common Issues

#### Python Version Issues
```bash
# Check Python version
python --version  # Should be 3.10+

# Use specific version if needed
python3.11 -m venv .venv
```

#### Permission Issues (Linux/macOS)
```bash
# Fix pip permissions
python -m pip install --user --upgrade pip

# Or use virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate
```

#### Node.js Issues
```bash
# Check Node.js version
node --version  # Should be 18+

# Clear npm cache if installation fails
npm cache clean --force
```

#### Module Import Errors
```bash
# Ensure you're in virtual environment
which python  # Should show .venv path

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Use different port
python -m uvicorn app.main:app --port 8001
```

### Performance Issues

#### Slow Dependency Resolution
- **Cause**: Large dependency trees
- **Solution**: Use lockfiles (package-lock.json, poetry.lock) for faster parsing

#### API Rate Limiting
- **Cause**: Too many OSV.dev requests
- **Solution**: Caching is automatic; wait a few minutes and retry

#### Memory Usage
- **Cause**: Large projects with many dependencies  
- **Solution**: Process in smaller batches or increase system memory

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: Backend logs show detailed error information
2. **Run tests**: `./run_tests.py` can identify environment issues
3. **GitHub Issues**: Report bugs at [repository issues](https://github.com/yourusername/depscan/issues)
4. **Documentation**: Check [Architecture docs](../architecture/overview.md) for system details

---

## 🔄 Updating DepScan

### Docker Update
```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose down
docker-compose up --build
```

### Local Update
```bash
# Pull latest changes
git pull origin main

# Update Python dependencies
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# Update frontend (if using)
cd frontend
npm install
npm run build
```

---

## 🚀 Next Steps

After successful installation:

1. **📖 Read the [CLI Usage Guide](cli-usage.md)** - Learn command-line options
2. **🌐 Explore the [Web Interface Guide](web-interface.md)** - Use the dashboard
3. **⚙️ Review [Configuration Options](configuration.md)** - Customize behavior
4. **🔧 Check [Development Setup](../development/setup.md)** - If contributing code

---

## 📋 Installation Checklist

- [ ] **Python 3.10+** installed and verified
- [ ] **Virtual environment** created and activated  
- [ ] **Backend dependencies** installed successfully
- [ ] **CLI help command** works
- [ ] **Test scan** completes without errors
- [ ] **Web server** starts (if using web interface)
- [ ] **Frontend built** (if using web interface)
- [ ] **Test suite** passes (optional but recommended)

✅ **Installation Complete!** You're ready to start scanning for vulnerabilities.