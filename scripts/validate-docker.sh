#!/bin/bash
# Docker validation script for DepScan
set -e

echo "=== DepScan Docker Validation Script ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${GREEN}ℹ${NC} $1"
}

# Check Docker and Docker Compose
echo "Checking Docker setup..."
docker --version > /dev/null 2>&1
print_status $? "Docker is installed"

docker compose version > /dev/null 2>&1
print_status $? "Docker Compose is installed"

# Check for required files
echo ""
echo "Checking required files..."

FILES=(
    "Dockerfile.dev"
    "Dockerfile.staging" 
    "docker-compose.dev.yml"
    "docker-compose.staging.yml"
    "backend/requirements.txt"
    "frontend/package.json"
    "frontend/Dockerfile.dev"
    "frontend/Dockerfile.staging"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "Found $file"
    else
        print_status 1 "Missing $file"
    fi
done

# Check for directories
echo ""
echo "Checking required directories..."

DIRS=(
    "backend"
    "frontend"
    "data"
    "logs"
    "scan-projects"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        print_status 0 "Found directory $dir"
    else
        print_status 1 "Missing directory $dir"
        if [ "$dir" == "data" ] || [ "$dir" == "logs" ] || [ "$dir" == "scan-projects" ]; then
            print_info "Creating missing directory: $dir"
            mkdir -p "$dir"
        fi
    fi
done

# Validate Python imports
echo ""
echo "Validating Python module structure..."

PYTHON_MODULES=(
    "backend/core/__init__.py"
    "backend/core/resolver/__init__.py" 
    "backend/core/resolver/factories/__init__.py"
    "backend/core/resolver/parsers/__init__.py"
    "backend/core/resolver/parsers/javascript/__init__.py"
    "backend/core/resolver/parsers/python/__init__.py"
    "backend/core/resolver/utils/__init__.py"
    "backend/web/__init__.py"
)

for module in "${PYTHON_MODULES[@]}"; do
    if [ -f "$module" ]; then
        print_status 0 "Found Python module $module"
    else
        print_status 1 "Missing Python module $module"
    fi
done

# Check Docker Compose syntax
echo ""
echo "Validating Docker Compose files..."

docker compose -f docker-compose.dev.yml config > /dev/null 2>&1
print_status $? "docker-compose.dev.yml syntax is valid"

docker compose -f docker-compose.staging.yml config > /dev/null 2>&1
print_status $? "docker-compose.staging.yml syntax is valid"

# Test development build
echo ""
echo "Testing development build..."
print_warning "This will attempt to build the development images..."

if docker compose -f docker-compose.dev.yml build --no-cache > /dev/null 2>&1; then
    print_status 0 "Development build successful"
else
    print_status 1 "Development build failed"
    echo ""
    print_info "To see detailed build output, run:"
    echo "docker compose -f docker-compose.dev.yml build --no-cache"
fi

# Test staging build
echo ""
echo "Testing staging build..."
print_warning "This will attempt to build the staging images..."

if docker compose -f docker-compose.staging.yml build --no-cache > /dev/null 2>&1; then
    print_status 0 "Staging build successful"
else
    print_status 1 "Staging build failed"
    echo ""
    print_info "To see detailed build output, run:"
    echo "docker compose -f docker-compose.staging.yml build --no-cache"
fi

echo ""
print_info "Validation complete!"
echo ""
print_info "To start development environment:"
echo "  docker compose -f docker-compose.dev.yml up"
echo ""
print_info "To start staging environment:"
echo "  docker compose -f docker-compose.staging.yml up"
echo ""
print_info "To run without building:"
echo "  docker compose -f docker-compose.dev.yml up --build"