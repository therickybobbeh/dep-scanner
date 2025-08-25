#!/bin/bash

# DepScan Development Environment Setup Script
# This script sets up the development environment for DepScan

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emojis for better UX
ROCKET="🚀"
CHECK="✅"
CROSS="❌"
INFO="ℹ️"
WARNING="⚠️"
GEAR="⚙️"
PACKAGE="📦"

log_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

log_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

log_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

log_step() {
    echo -e "${CYAN}${GEAR} $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        log_success "$1 is installed"
        return 0
    else
        log_error "$1 is not installed"
        return 1
    fi
}

install_requirements() {
    log_header "Checking System Requirements"
    
    local missing_deps=0
    
    # Check Python
    if check_command python3; then
        python_version=$(python3 --version | cut -d' ' -f2)
        log_info "Python version: $python_version"
    else
        log_error "Python 3 is required but not installed"
        echo "  Install Python 3.11+ from: https://python.org"
        ((missing_deps++))
    fi
    
    # Check Node.js
    if check_command node; then
        node_version=$(node --version)
        log_info "Node.js version: $node_version"
    else
        log_error "Node.js is required but not installed"
        echo "  Install Node.js 18+ from: https://nodejs.org"
        ((missing_deps++))
    fi
    
    # Check npm
    if check_command npm; then
        npm_version=$(npm --version)
        log_info "npm version: $npm_version"
    else
        log_error "npm is required but not installed"
        ((missing_deps++))
    fi
    
    # Check Docker (optional but recommended)
    if check_command docker; then
        docker_version=$(docker --version)
        log_info "Docker version: $docker_version"
        DOCKER_AVAILABLE=true
    else
        log_warning "Docker is not installed (optional but recommended)"
        echo "  Install Docker from: https://docker.com"
        DOCKER_AVAILABLE=false
    fi
    
    # Check Docker Compose (optional but recommended)
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        log_success "Docker Compose is available"
        DOCKER_COMPOSE_AVAILABLE=true
    else
        log_warning "Docker Compose is not available (optional but recommended)"
        DOCKER_COMPOSE_AVAILABLE=false
    fi
    
    if [ $missing_deps -gt 0 ]; then
        log_error "Please install missing dependencies and run this script again"
        exit 1
    fi
    
    log_success "All required dependencies are installed!"
    echo ""
}

setup_environment() {
    log_header "Setting Up Environment Files"
    
    # Backend environment
    if [ ! -f ".env" ]; then
        log_step "Creating backend .env file from template..."
        cp .env.development .env
        log_success "Backend .env file created"
    else
        log_info "Backend .env file already exists"
    fi
    
    # Frontend environment
    if [ ! -f "frontend/.env" ]; then
        log_step "Creating frontend .env file from template..."
        cp frontend/.env.development frontend/.env
        log_success "Frontend .env file created"
    else
        log_info "Frontend .env file already exists"
    fi
    
    echo ""
}

setup_backend() {
    log_header "Setting Up Backend"
    
    log_step "Creating Python virtual environment..."
    cd backend
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    log_step "Activating virtual environment and installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Backend dependencies installed"
    cd ..
    echo ""
}

setup_frontend() {
    log_header "Setting Up Frontend"
    
    log_step "Installing frontend dependencies..."
    cd frontend
    npm install
    
    log_success "Frontend dependencies installed"
    cd ..
    echo ""
}

setup_data_directories() {
    log_header "Creating Data Directories"
    
    log_step "Creating data and logs directories..."
    mkdir -p data
    mkdir -p logs
    mkdir -p backend/data
    mkdir -p backend/logs
    
    log_success "Data directories created"
    echo ""
}

show_next_steps() {
    log_header "Setup Complete!"
    
    echo -e "${GREEN}${ROCKET} Your DepScan development environment is ready!${NC}"
    echo ""
    echo -e "${CYAN}Quick Start Options:${NC}"
    echo ""
    
    if [ "$DOCKER_AVAILABLE" = true ] && [ "$DOCKER_COMPOSE_AVAILABLE" = true ]; then
        echo -e "${BLUE}🐳 Option 1: Docker Development (Recommended)${NC}"
        echo "   make start-docker-dev     # Start both frontend and backend"
        echo "   make stop-docker-dev      # Stop the development environment"
        echo ""
    fi
    
    echo -e "${BLUE}💻 Option 2: Manual Development${NC}"
    echo "   # Terminal 1 (Backend):"
    echo "   cd backend && source .venv/bin/activate"
    echo "   python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "   # Terminal 2 (Frontend):"
    echo "   cd frontend && npm run dev"
    echo ""
    
    echo -e "${CYAN}Development URLs:${NC}"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    
    echo -e "${CYAN}Useful Commands:${NC}"
    echo "   make help           # Show all available commands"
    echo "   make test           # Run tests"
    echo "   make lint           # Run linting"
    echo "   make format         # Format code"
    echo ""
    
    echo -e "${YELLOW}${INFO} Check out the README.md for more detailed information!${NC}"
}

main() {
    echo -e "${PURPLE}"
    cat << "EOF"
    ____             ____                  
   |  _ \  ___ _ __ / ___|  ___ __ _ _ __  
   | | | |/ _ \ '_ \\___ \ / __/ _` | '_ \ 
   | |_| |  __/ |_) |___) | (_| (_| | | | |
   |____/ \___| .__/|____/ \___\__,_|_| |_|
              |_|                         
EOF
    echo -e "${NC}"
    echo -e "${CYAN}Development Environment Setup${NC}"
    echo ""
    
    # Run setup steps
    install_requirements
    setup_environment
    setup_data_directories
    setup_backend
    setup_frontend
    show_next_steps
}

# Help message
show_help() {
    cat << EOF
DepScan Development Setup Script

Usage: $0 [options]

Options:
  -h, --help    Show this help message
  --skip-deps   Skip dependency check (not recommended)

This script will:
1. Check system requirements (Python 3.11+, Node.js 18+, npm)
2. Set up environment files (.env)
3. Create Python virtual environment
4. Install backend dependencies
5. Install frontend dependencies
6. Create necessary directories
7. Show next steps

EOF
}

# Parse command line arguments
SKIP_DEPS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [ ! -f "setup-dev.sh" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    log_error "Please run this script from the DepScan project root directory"
    exit 1
fi

# Run main function
main