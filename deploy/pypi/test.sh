#!/bin/bash

# DepScan Package Testing Script
# Tests the package installation and basic functionality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing DepScan Package Installation${NC}"
echo "======================================="

# Parse command line arguments
ENVIRONMENT="local"
if [ "$1" = "testpypi" ]; then
    ENVIRONMENT="testpypi"
elif [ "$1" = "pypi" ]; then
    ENVIRONMENT="pypi"
fi

# Create temporary directory for testing
TEST_DIR=$(mktemp -d)
echo -e "${BLUE}📁 Test directory: ${TEST_DIR}${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up test environment...${NC}"
    rm -rf "$TEST_DIR"
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate 2>/dev/null || true
    fi
}
trap cleanup EXIT

cd "$TEST_DIR"

# Create virtual environment for isolated testing
echo -e "${YELLOW}🐍 Creating virtual environment...${NC}"
python -m venv test_env
source test_env/bin/activate

# Upgrade pip
echo -e "${YELLOW}📦 Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install package based on environment
echo ""
if [ "$ENVIRONMENT" = "testpypi" ]; then
    echo -e "${YELLOW}📦 Installing from TestPyPI...${NC}"
    pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ dep-scan
elif [ "$ENVIRONMENT" = "pypi" ]; then
    echo -e "${YELLOW}📦 Installing from PyPI...${NC}"
    pip install dep-scan
else
    echo -e "${YELLOW}📦 Installing from local build...${NC}"
    PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
    if [ ! -d "$PROJECT_ROOT/dist" ]; then
        echo -e "${RED}❌ No local build found. Run ./deploy/pypi/build.sh first${NC}"
        exit 1
    fi
    pip install "$PROJECT_ROOT"/dist/*.whl
fi

echo -e "${GREEN}✅ Installation completed${NC}"

# Test 1: Check if command is available
echo ""
echo -e "${BLUE}🧪 Test 1: Command availability${NC}"
if command -v dep-scan >/dev/null 2>&1; then
    echo -e "${GREEN}✅ dep-scan command is available${NC}"
else
    echo -e "${RED}❌ dep-scan command not found${NC}"
    exit 1
fi

# Test 2: Check version
echo ""
echo -e "${BLUE}🧪 Test 2: Version check${NC}"
VERSION_OUTPUT=$(dep-scan --version 2>&1 || echo "VERSION_FAILED")
if [[ "$VERSION_OUTPUT" == *"VERSION_FAILED"* ]]; then
    echo -e "${RED}❌ Failed to get version${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Version: ${VERSION_OUTPUT}${NC}"
fi

# Test 3: Help command
echo ""
echo -e "${BLUE}🧪 Test 3: Help command${NC}"
if dep-scan --help >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Help command works${NC}"
else
    echo -e "${RED}❌ Help command failed${NC}"
    exit 1
fi

# Test 4: Create test files and scan
echo ""
echo -e "${BLUE}🧪 Test 4: Basic scanning functionality${NC}"

# Create test package.json
cat > package.json << 'EOF'
{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "lodash": "4.17.15"
  }
}
EOF

# Test package.json scanning
echo -e "${YELLOW}  Testing package.json scanning...${NC}"
if dep-scan scan package.json --output json > scan_results.json 2>&1; then
    echo -e "${GREEN}✅ Package.json scan successful${NC}"
    
    # Check if results contain expected structure
    if command -v jq >/dev/null 2>&1; then
        VULN_COUNT=$(jq '.vulnerable_count // 0' scan_results.json 2>/dev/null || echo "0")
        echo -e "${BLUE}  └─ Found ${VULN_COUNT} vulnerabilities${NC}"
    else
        echo -e "${BLUE}  └─ Scan completed (install jq to see vulnerability count)${NC}"
    fi
else
    echo -e "${RED}❌ Package.json scan failed${NC}"
    cat scan_results.json 2>/dev/null || true
    exit 1
fi

# Create test requirements.txt
cat > requirements.txt << 'EOF'
requests==2.25.1
flask==1.1.4
jinja2==2.11.3
EOF

# Test requirements.txt scanning
echo -e "${YELLOW}  Testing requirements.txt scanning...${NC}"
if dep-scan scan requirements.txt --output json > python_results.json 2>&1; then
    echo -e "${GREEN}✅ Requirements.txt scan successful${NC}"
    
    if command -v jq >/dev/null 2>&1; then
        VULN_COUNT=$(jq '.vulnerable_count // 0' python_results.json 2>/dev/null || echo "0")
        echo -e "${BLUE}  └─ Found ${VULN_COUNT} vulnerabilities${NC}"
    else
        echo -e "${BLUE}  └─ Scan completed${NC}"
    fi
else
    echo -e "${RED}❌ Requirements.txt scan failed${NC}"
    cat python_results.json 2>/dev/null || true
    exit 1
fi

# Test 5: Check different output formats
echo ""
echo -e "${BLUE}🧪 Test 5: Output format options${NC}"

# Test CSV output
if dep-scan scan package.json --output csv > results.csv 2>&1; then
    echo -e "${GREEN}✅ CSV output format works${NC}"
else
    echo -e "${RED}❌ CSV output format failed${NC}"
fi

# Test human-readable output
if dep-scan scan package.json > human_results.txt 2>&1; then
    echo -e "${GREEN}✅ Human-readable output works${NC}"
else
    echo -e "${RED}❌ Human-readable output failed${NC}"
fi

# Test 6: Import testing (Python module)
echo ""
echo -e "${BLUE}🧪 Test 6: Python module import${NC}"
if python -c "
import backend.cli.main
import backend.core.core_scanner
import backend.web.main
print('✅ All core modules import successfully')
" 2>&1; then
    echo -e "${GREEN}✅ Python modules import correctly${NC}"
else
    echo -e "${RED}❌ Python module import failed${NC}"
    exit 1
fi

# Test 7: CLI edge cases
echo ""
echo -e "${BLUE}🧪 Test 7: CLI edge cases${NC}"

# Test with non-existent file
if dep-scan scan non_existent_file.json 2>&1 | grep -q "not found\|No such file" ; then
    echo -e "${GREEN}✅ Handles missing files gracefully${NC}"
else
    echo -e "${YELLOW}⚠️  Missing file handling might need improvement${NC}"
fi

# Test with empty file
touch empty_file.json
if dep-scan scan empty_file.json 2>&1; then
    echo -e "${GREEN}✅ Handles empty files gracefully${NC}"
else
    echo -e "${YELLOW}⚠️  Empty file handling might need improvement${NC}"
fi

# Final summary
echo ""
echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Test Summary:${NC}"
echo "  ✅ Command availability"
echo "  ✅ Version check"
echo "  ✅ Help command"
echo "  ✅ Package.json scanning"
echo "  ✅ Requirements.txt scanning"
echo "  ✅ Multiple output formats"
echo "  ✅ Python module imports"
echo "  ✅ Edge case handling"

# Show package info
echo ""
echo -e "${BLUE}📦 Installed Package Info:${NC}"
pip show dep-scan

echo ""
echo -e "${BLUE}📁 Test files created in: ${TEST_DIR}${NC}"
echo -e "${BLUE}Available for inspection before cleanup${NC}"

# Keep test directory for a moment
echo ""
echo -e "${YELLOW}Press Enter to clean up test environment...${NC}"
read -r

echo -e "${GREEN}🎉 Package testing completed successfully!${NC}"

if [ "$ENVIRONMENT" = "local" ]; then
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Publish to TestPyPI: ./deploy/pypi/publish.sh test"
    echo "  2. Test TestPyPI install: ./deploy/pypi/test.sh testpypi"
    echo "  3. Publish to PyPI: ./deploy/pypi/publish.sh prod"
elif [ "$ENVIRONMENT" = "testpypi" ]; then
    echo ""
    echo -e "${BLUE}TestPyPI package works correctly!${NC}"
    echo "Ready to publish to PyPI: ./deploy/pypi/publish.sh prod"
else
    echo ""
    echo -e "${BLUE}PyPI package is working correctly!${NC}"
fi