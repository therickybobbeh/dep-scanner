#!/bin/bash

# Multi-Vuln-Scanner Package Publishing Script
# Currently: TestPyPI only (production PyPI disabled)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to test environment
ENVIRONMENT="test"

# Parse command line arguments
if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
    echo -e "${RED}❌ Production PyPI publishing is currently DISABLED${NC}"
    echo -e "${YELLOW}We are using TestPyPI only for now${NC}"
    echo "Use: $0 test (or run without arguments)"
    exit 1
elif [ "$1" = "test" ] || [ "$1" = "testpypi" ] || [ -z "$1" ]; then
    ENVIRONMENT="test"
elif [ -n "$1" ]; then
    echo -e "${RED}❌ Invalid environment: $1${NC}"
    echo "Usage: $0 [test]"
    echo "  test: Publish to TestPyPI (default and only option)"
    echo "  prod: DISABLED - Production PyPI publishing not available yet"
    exit 1
fi

# Set repository URL (TestPyPI only)
REPO_URL="https://test.pypi.org/legacy/"
REPO_NAME="TestPyPI"
echo -e "${BLUE}📦 Publishing to TestPyPI (testing only)${NC}"

echo "=================================="

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Verify dist directory exists
if [ ! -d "dist" ] || [ -z "$(ls -A dist/)" ]; then
    echo -e "${RED}❌ No packages found in dist/ directory${NC}"
    echo "Run ./deploy/pypi/build.sh first to build packages"
    exit 1
fi

# Check if twine is installed
if ! command -v twine >/dev/null 2>&1; then
    echo -e "${YELLOW}📦 Installing twine...${NC}"
    python -m pip install twine
fi

# Get version from pyproject.toml
VERSION=$(python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || echo "unknown")
echo -e "${BLUE}📦 Publishing version: ${VERSION}${NC}"

# List packages to be uploaded
echo ""
echo -e "${BLUE}📦 Packages to upload:${NC}"
ls -la dist/

# TestPyPI confirmation
echo ""
echo -e "${YELLOW}📝 Publishing to TestPyPI for testing and validation${NC}"
echo -e "${YELLOW}This is safe - TestPyPI is for testing packages before production${NC}"
echo ""

# Run final validation
echo -e "${YELLOW}🔍 Running final validation...${NC}"
twine check dist/*

# Upload packages
echo ""
echo -e "${YELLOW}📤 Uploading to ${REPO_NAME}...${NC}"

# Try to upload using stored credentials first
if twine upload --repository-url "$REPO_URL" dist/* 2>/dev/null; then
    echo -e "${GREEN}✅ Upload successful!${NC}"
else
    echo -e "${YELLOW}🔐 Stored credentials not found or invalid. Please enter credentials:${NC}"
    echo ""
    echo "Enter your TestPyPI username (__token__ if using API token):"
    echo "Enter your TestPyPI password (API token if username is __token__):"
    echo ""
    
    twine upload --repository-url "$REPO_URL" dist/*
fi

# Success message and next steps
echo ""
echo -e "${GREEN}🎉 Package published successfully to ${REPO_NAME}!${NC}"
echo ""

echo -e "${BLUE}📦 Your package is now available on TestPyPI:${NC}"
echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner==$VERSION"
echo ""
echo -e "${BLUE}Package URL:${NC}"
echo "  https://test.pypi.org/project/multi-vuln-scanner/$VERSION/"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Test installation: make -f Makefile.publish verify-install-test"
echo "  2. Run functionality tests: scripts/test-package.py"
echo "  3. Monitor cross-platform tests in GitHub Actions"
echo "  4. Create GitHub release when ready: git tag v$VERSION && git push origin v$VERSION"
echo ""
echo -e "${YELLOW}Production PyPI:${NC}"
echo "  Production publishing will be enabled after thorough TestPyPI validation"

echo ""
echo -e "${BLUE}Remember:${NC}"
echo "  • Package versions cannot be re-uploaded (even on TestPyPI)"
echo "  • TestPyPI packages are automatically cleaned up periodically"
echo "  • Keep your API tokens secure"
echo "  • Production PyPI will be enabled once TestPyPI validation is complete"