#!/bin/bash

# DepScan Release Build Script
# Builds and packages DepScan for PyPI distribution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the correct directory
if [[ ! -f "pyproject.toml" ]]; then
    log_error "pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

# Check required tools
for tool in python npm; do
    if ! command -v $tool &> /dev/null; then
        log_error "$tool is not installed or not in PATH"
        exit 1
    fi
done

log_info "Starting DepScan release build..."

# Clean previous builds
log_info "Cleaning previous builds..."
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/
rm -rf backend/*.egg-info/

# Build frontend
log_info "Building frontend..."
cd frontend
if [[ ! -f "package.json" ]]; then
    log_error "frontend/package.json not found"
    exit 1
fi

npm ci
npm run build
cd ..

# Install build dependencies
log_info "Installing build dependencies..."
python -m pip install --upgrade pip build twine

# Build Python package
log_info "Building Python package..."
python -m build

# Check the built package
log_info "Checking built package..."
python -m twine check dist/*

# Run security scans on dependencies
log_info "Running security scans..."
if command -v safety &> /dev/null; then
    safety check
else
    log_warn "Safety not installed, skipping dependency security scan"
fi

# Optional: Test installation in a virtual environment
if [[ "$1" == "--test-install" ]]; then
    log_info "Testing installation in virtual environment..."
    python -m venv test-env
    source test-env/bin/activate
    pip install dist/*.whl
    dep-scan --help
    deactivate
    rm -rf test-env
    log_info "Installation test successful!"
fi

log_info "Build complete! Package files:"
ls -la dist/

echo
log_info "To publish to Test PyPI:"
echo "  python -m twine upload --repository testpypi dist/*"
echo
log_info "To publish to PyPI:"
echo "  python -m twine upload dist/*"
echo
log_info "Or use GitHub Actions by creating a release tag:"
echo "  git tag v1.0.0 && git push origin v1.0.0"