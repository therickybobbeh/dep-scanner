#!/bin/bash

# Deploy script for DepScan AWS infrastructure
# This script helps deploy local changes to AWS ECS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-1"
ECR_REGISTRY=""
BACKEND_ECR_REPO="depscan-prod-backend"
FRONTEND_ECR_REPO="depscan-prod-frontend"
ECS_CLUSTER="depscan-prod-cluster"
BACKEND_SERVICE="depscan-prod-backend"
FRONTEND_SERVICE="depscan-prod-frontend"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed and configured
check_aws_cli() {
    print_status "Checking AWS CLI configuration..."
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Get ECR registry URL
get_ecr_registry() {
    print_status "Getting ECR registry URL..."
    ECR_REGISTRY=$(aws ecr describe-registry --query 'registryId' --output text).dkr.ecr.$AWS_REGION.amazonaws.com
    print_success "ECR Registry: $ECR_REGISTRY"
}

# Login to ECR
ecr_login() {
    print_status "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    print_success "Logged in to ECR"
}

# Build and push backend image
build_push_backend() {
    print_status "Building backend image..."
    docker build --platform linux/amd64 -t $ECR_REGISTRY/$BACKEND_ECR_REPO:latest -f deploy/docker/Dockerfile.backend .
    
    print_status "Pushing backend image to ECR..."
    docker push $ECR_REGISTRY/$BACKEND_ECR_REPO:latest
    
    print_success "Backend image pushed successfully"
}

# Build and push frontend image
build_push_frontend() {
    print_status "Building frontend image..."
    docker build --platform linux/amd64 -t $ECR_REGISTRY/$FRONTEND_ECR_REPO:latest -f deploy/docker/Dockerfile.frontend .
    
    print_status "Pushing frontend image to ECR..."
    docker push $ECR_REGISTRY/$FRONTEND_ECR_REPO:latest
    
    print_success "Frontend image pushed successfully"
}

# Force update ECS services
update_services() {
    print_status "Updating ECS services..."
    
    # Force update backend service
    print_status "Updating backend service..."
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $BACKEND_SERVICE \
        --force-new-deployment \
        --query 'service.serviceName' \
        --output text
    
    # Force update frontend service
    print_status "Updating frontend service..."
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $FRONTEND_SERVICE \
        --force-new-deployment \
        --query 'service.serviceName' \
        --output text
    
    print_success "ECS services updated"
}

# Wait for services to be stable
wait_for_services() {
    print_status "Waiting for services to be stable (this may take a few minutes)..."
    
    print_status "Waiting for backend service..."
    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $BACKEND_SERVICE
    
    print_status "Waiting for frontend service..."
    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $FRONTEND_SERVICE
    
    print_success "All services are stable"
}

# Get service URLs
get_service_urls() {
    print_status "Getting service URLs..."
    
    # Get backend task public IP
    BACKEND_TASK_ARN=$(aws ecs list-tasks \
        --cluster $ECS_CLUSTER \
        --service-name $BACKEND_SERVICE \
        --query 'taskArns[0]' \
        --output text)
    
    if [ "$BACKEND_TASK_ARN" != "None" ] && [ "$BACKEND_TASK_ARN" != "" ]; then
        BACKEND_IP=$(aws ecs describe-tasks \
            --cluster $ECS_CLUSTER \
            --tasks $BACKEND_TASK_ARN \
            --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
            --output text)
        
        if [ "$BACKEND_IP" != "None" ] && [ "$BACKEND_IP" != "" ]; then
            BACKEND_PUBLIC_IP=$(aws ec2 describe-network-interfaces \
                --network-interface-ids $BACKEND_IP \
                --query 'NetworkInterfaces[0].Association.PublicIp' \
                --output text)
        fi
    fi
    
    # Get frontend task public IP
    FRONTEND_TASK_ARN=$(aws ecs list-tasks \
        --cluster $ECS_CLUSTER \
        --service-name $FRONTEND_SERVICE \
        --query 'taskArns[0]' \
        --output text)
    
    if [ "$FRONTEND_TASK_ARN" != "None" ] && [ "$FRONTEND_TASK_ARN" != "" ]; then
        FRONTEND_IP=$(aws ecs describe-tasks \
            --cluster $ECS_CLUSTER \
            --tasks $FRONTEND_TASK_ARN \
            --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
            --output text)
        
        if [ "$FRONTEND_IP" != "None" ] && [ "$FRONTEND_IP" != "" ]; then
            FRONTEND_PUBLIC_IP=$(aws ec2 describe-network-interfaces \
                --network-interface-ids $FRONTEND_IP \
                --query 'NetworkInterfaces[0].Association.PublicIp' \
                --output text)
        fi
    fi
    
    echo ""
    print_success "Deployment completed successfully!"
    echo ""
    echo -e "${GREEN}🌐 Access URLs:${NC}"
    if [ "$BACKEND_PUBLIC_IP" != "None" ] && [ "$BACKEND_PUBLIC_IP" != "" ]; then
        echo -e "  Backend API: ${BLUE}http://$BACKEND_PUBLIC_IP:8000${NC}"
        echo -e "  API Docs: ${BLUE}http://$BACKEND_PUBLIC_IP:8000/docs${NC}"
        echo -e "  Health Check: ${BLUE}http://$BACKEND_PUBLIC_IP:8000/health${NC}"
    fi
    if [ "$FRONTEND_PUBLIC_IP" != "None" ] && [ "$FRONTEND_PUBLIC_IP" != "" ]; then
        echo -e "  Frontend: ${BLUE}http://$FRONTEND_PUBLIC_IP:8080${NC}"
    fi
    echo ""
}

# Main deployment function
deploy() {
    echo -e "${BLUE}🚀 Starting DepScan deployment...${NC}"
    echo ""
    
    check_aws_cli
    check_docker
    get_ecr_registry
    ecr_login
    
    # Ask what to deploy
    echo ""
    print_status "What would you like to deploy?"
    echo "1) Backend only"
    echo "2) Frontend only"  
    echo "3) Both backend and frontend"
    echo -n "Enter your choice (1-3): "
    read -r choice
    
    case $choice in
        1)
            build_push_backend
            print_status "Updating backend service..."
            aws ecs update-service \
                --cluster $ECS_CLUSTER \
                --service $BACKEND_SERVICE \
                --force-new-deployment \
                --query 'service.serviceName' \
                --output text
            ;;
        2)
            build_push_frontend
            print_status "Updating frontend service..."
            aws ecs update-service \
                --cluster $ECS_CLUSTER \
                --service $FRONTEND_SERVICE \
                --force-new-deployment \
                --query 'service.serviceName' \
                --output text
            ;;
        3)
            build_push_backend
            build_push_frontend
            update_services
            ;;
        *)
            print_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac
    
    wait_for_services
    get_service_urls
}

# Check for help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "DepScan Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script builds Docker images and deploys them to AWS ECS."
    echo ""
    echo "Prerequisites:"
    echo "  - AWS CLI installed and configured"
    echo "  - Docker installed and running"
    echo "  - Appropriate AWS permissions for ECS and ECR"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "The script will prompt you to choose what to deploy:"
    echo "  1) Backend only"
    echo "  2) Frontend only"
    echo "  3) Both backend and frontend"
    exit 0
fi

# Run deployment
deploy