#!/bin/bash

# DepScan Package Publishing Script
# Publishes to TestPyPI or PyPI

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
    ENVIRONMENT="prod"
elif [ "$1" = "test" ] || [ "$1" = "testpypi" ]; then
    ENVIRONMENT="test"
elif [ -n "$1" ]; then
    echo -e "${RED}❌ Invalid environment: $1${NC}"
    echo "Usage: $0 [test|prod]"
    echo "  test: Publish to TestPyPI (default)"
    echo "  prod: Publish to PyPI"
    exit 1
fi

# Set repository URL based on environment
if [ "$ENVIRONMENT" = "prod" ]; then
    REPO_URL="https://upload.pypi.org/legacy/"
    REPO_NAME="PyPI"
    echo -e "${BLUE}📦 Publishing to PyPI (PRODUCTION)${NC}"
else
    REPO_URL="https://test.pypi.org/legacy/"
    REPO_NAME="TestPyPI"
    echo -e "${BLUE}📦 Publishing to TestPyPI (testing)${NC}"
fi

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

# Production safety check
if [ "$ENVIRONMENT" = "prod" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: You are about to publish to PyPI (PRODUCTION)${NC}"
    echo -e "${YELLOW}This will make the package publicly available to all pip users.${NC}"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Publishing cancelled."
        exit 0
    fi
    
    # Additional check - ensure TestPyPI was tested first
    echo ""
    echo -e "${YELLOW}Have you tested this version on TestPyPI first? (y/N): ${NC}"
    read -p "" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Please test on TestPyPI first with: ./deploy/pypi/publish.sh test${NC}"
        exit 0
    fi
fi

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
    if [ "$ENVIRONMENT" = "prod" ]; then
        echo "Enter your PyPI username (__token__ if using API token):"
        echo "Enter your PyPI password (API token if username is __token__):"
    else
        echo "Enter your TestPyPI username (__token__ if using API token):"
        echo "Enter your TestPyPI password (API token if username is __token__):"
    fi
    echo ""
    
    twine upload --repository-url "$REPO_URL" dist/*
fi

# Success message and next steps
echo ""
echo -e "${GREEN}🎉 Package published successfully to ${REPO_NAME}!${NC}"
echo ""

if [ "$ENVIRONMENT" = "prod" ]; then
    echo -e "${BLUE}📦 Your package is now available:${NC}"
    echo "  pip install dep-scan==$VERSION"
    echo ""
    echo -e "${BLUE}Package URL:${NC}"
    echo "  https://pypi.org/project/dep-scan/$VERSION/"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Test installation: pip install --upgrade dep-scan"
    echo "  2. Create GitHub release: git tag v$VERSION && git push origin v$VERSION"
    echo "  3. Update documentation with new features"
    echo "  4. Announce the release"
else
    echo -e "${BLUE}📦 Your package is now available on TestPyPI:${NC}"
    echo "  pip install --index-url https://test.pypi.org/simple/ dep-scan==$VERSION"
    echo ""
    echo -e "${BLUE}Package URL:${NC}"
    echo "  https://test.pypi.org/project/dep-scan/$VERSION/"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Test installation: ./deploy/pypi/test.sh"
    echo "  2. If tests pass, publish to PyPI: ./deploy/pypi/publish.sh prod"
fi

echo ""
echo -e "${BLUE}Remember:${NC}"
echo "  • Package versions cannot be re-uploaded"
echo "  • Always test on TestPyPI before publishing to PyPI"
echo "  • Keep your API tokens secure"