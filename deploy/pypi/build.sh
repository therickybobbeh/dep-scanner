#!/bin/bash

# DepScan Package Build Script
# Builds wheel and source distribution for PyPI publishing

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  Building DepScan Package${NC}"
echo "=================================="

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}📍 Working directory: ${PROJECT_ROOT}${NC}"

# Clean previous builds
echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Verify pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ pyproject.toml not found in project root${NC}"
    exit 1
fi

# Check if build tools are installed
echo -e "${YELLOW}🔧 Checking build dependencies...${NC}"
if ! python -m pip show build >/dev/null 2>&1; then
    echo -e "${YELLOW}📦 Installing build dependencies...${NC}"
    python -m pip install build twine
fi

# Verify project can be imported (basic smoke test)
echo -e "${YELLOW}🧪 Running basic smoke test...${NC}"
if ! python -c "import backend; print('✅ Import successful')" 2>/dev/null; then
    echo -e "${RED}❌ Cannot import backend module. Check your project structure.${NC}"
    exit 1
fi

# Get version from pyproject.toml
VERSION=$(python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || echo "unknown")
echo -e "${BLUE}📦 Building version: ${VERSION}${NC}"

# Build the package
echo -e "${YELLOW}🔨 Building wheel and source distribution...${NC}"
python -m build --wheel --sdist

# Verify build output
if [ ! -d "dist" ] || [ -z "$(ls -A dist/)" ]; then
    echo -e "${RED}❌ Build failed - no files in dist/ directory${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build completed successfully!${NC}"
echo ""
echo -e "${BLUE}📦 Built packages:${NC}"
ls -la dist/

# Basic validation of built packages
echo ""
echo -e "${YELLOW}🔍 Validating built packages...${NC}"

# Check wheel
WHEEL_FILE=$(find dist/ -name "*.whl" | head -1)
if [ -n "$WHEEL_FILE" ]; then
    echo -e "${GREEN}✅ Wheel: $(basename "$WHEEL_FILE")${NC}"
    # Validate wheel structure
    python -m zipfile -l "$WHEEL_FILE" | grep -q "backend/" && echo -e "${GREEN}  └─ Contains backend/ module${NC}" || echo -e "${RED}  └─ Missing backend/ module${NC}"
else
    echo -e "${RED}❌ No wheel file found${NC}"
fi

# Check source distribution
SDIST_FILE=$(find dist/ -name "*.tar.gz" | head -1)
if [ -n "$SDIST_FILE" ]; then
    echo -e "${GREEN}✅ Source distribution: $(basename "$SDIST_FILE")${NC}"
else
    echo -e "${RED}❌ No source distribution found${NC}"
fi

# Run twine check for validation
if command -v twine >/dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}🔍 Running twine check...${NC}"
    if twine check dist/*; then
        echo -e "${GREEN}✅ All packages pass twine validation${NC}"
    else
        echo -e "${RED}❌ Packages failed twine validation${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Skipping twine check (not installed)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Package build completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Test the package: ./deploy/pypi/test.sh"
echo "  2. Publish to TestPyPI: ./deploy/pypi/publish.sh test"
echo "  3. Publish to PyPI: ./deploy/pypi/publish.sh prod"
echo ""
echo -e "${BLUE}Package contents:${NC}"
echo "$(ls -1 dist/)"