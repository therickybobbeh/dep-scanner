#!/bin/bash

# DepScan AWS Deployment Script
# This script helps with initial deployment and management tasks

set -e

# Configuration
PROJECT_NAME="depscan"
ENVIRONMENT="prod"
AWS_REGION="us-east-1"
TERRAFORM_DIR="./deploy/terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured. Run 'aws configure' first."
        exit 1
    fi
    
    print_success "All prerequisites are met."
}

# Function to initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    cd "$TERRAFORM_DIR"
    terraform init
    cd - > /dev/null
    print_success "Terraform initialized successfully."
}

# Function to plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    cd "$TERRAFORM_DIR"
    terraform plan -var-file="terraform.tfvars" || terraform plan
    cd - > /dev/null
}

# Function to apply Terraform deployment
apply_terraform() {
    print_status "Applying Terraform deployment..."
    cd "$TERRAFORM_DIR"
    terraform apply -auto-approve -var-file="terraform.tfvars" || terraform apply -auto-approve
    cd - > /dev/null
    print_success "Infrastructure deployed successfully."
}

# Function to get Terraform outputs
get_outputs() {
    print_status "Getting deployment information..."
    cd "$TERRAFORM_DIR"
    
    echo ""
    echo "=== Deployment Information ==="
    echo ""
    
    ALB_URL=$(terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
    BACKEND_ECR=$(terraform output -raw backend_ecr_repository_url 2>/dev/null || echo "Not available")
    FRONTEND_ECR=$(terraform output -raw frontend_ecr_repository_url 2>/dev/null || echo "Not available")
    GITHUB_ROLE=$(terraform output -raw github_actions_role_arn 2>/dev/null || echo "Not available")
    
    echo "Application URL: $ALB_URL"
    echo "Backend ECR URL: $BACKEND_ECR"
    echo "Frontend ECR URL: $FRONTEND_ECR"
    echo "GitHub Actions Role ARN: $GITHUB_ROLE"
    echo ""
    
    cd - > /dev/null
}

# Function to build and push initial images
build_and_push() {
    print_status "Building and pushing Docker images..."
    
    # Get ECR registry URL
    cd "$TERRAFORM_DIR"
    ECR_REGISTRY=$(terraform output -raw backend_ecr_repository_url | cut -d'/' -f1)
    BACKEND_REPO=$(terraform output -raw backend_ecr_repository_url | cut -d'/' -f2)
    FRONTEND_REPO=$(terraform output -raw frontend_ecr_repository_url | cut -d'/' -f2)
    cd - > /dev/null
    
    # Login to ECR
    print_status "Logging into ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
    
    # Build and push backend image
    print_status "Building backend image..."
    docker build -t "${ECR_REGISTRY}/${BACKEND_REPO}:latest" -f deploy/docker/Dockerfile.backend .
    
    print_status "Pushing backend image..."
    docker push "${ECR_REGISTRY}/${BACKEND_REPO}:latest"
    
    # Build and push frontend image
    print_status "Building frontend image..."
    docker build -t "${ECR_REGISTRY}/${FRONTEND_REPO}:latest" -f deploy/docker/Dockerfile.frontend .
    
    print_status "Pushing frontend image..."
    docker push "${ECR_REGISTRY}/${FRONTEND_REPO}:latest"
    
    print_success "Docker images built and pushed successfully."
}

# Function to update ECS services
update_services() {
    print_status "Updating ECS services..."
    
    cd "$TERRAFORM_DIR"
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    BACKEND_SERVICE=$(terraform output -raw backend_service_name)
    FRONTEND_SERVICE=$(terraform output -raw frontend_service_name)
    cd - > /dev/null
    
    # Force update services to pull new images
    aws ecs update-service --cluster "$CLUSTER_NAME" --service "$BACKEND_SERVICE" --force-new-deployment --region "$AWS_REGION"
    aws ecs update-service --cluster "$CLUSTER_NAME" --service "$FRONTEND_SERVICE" --force-new-deployment --region "$AWS_REGION"
    
    print_success "ECS services updated successfully."
}

# Function to check deployment status
check_status() {
    print_status "Checking deployment status..."
    
    cd "$TERRAFORM_DIR"
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    BACKEND_SERVICE=$(terraform output -raw backend_service_name)
    FRONTEND_SERVICE=$(terraform output -raw frontend_service_name)
    cd - > /dev/null
    
    echo ""
    echo "=== Service Status ==="
    echo ""
    
    aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$BACKEND_SERVICE" --region "$AWS_REGION" --query 'services[0].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' --output table
    aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$FRONTEND_SERVICE" --region "$AWS_REGION" --query 'services[0].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}' --output table
}

# Function to show logs
show_logs() {
    print_status "Showing recent logs..."
    
    cd "$TERRAFORM_DIR"
    LOG_GROUP=$(terraform output -raw cloudwatch_log_group_name)
    cd - > /dev/null
    
    echo ""
    echo "=== Recent Backend Logs ==="
    aws logs tail "$LOG_GROUP" --log-stream-names "backend" --since 10m --region "$AWS_REGION" || echo "No recent backend logs found"
    
    echo ""
    echo "=== Recent Frontend Logs ==="
    aws logs tail "$LOG_GROUP" --log-stream-names "frontend" --since 10m --region "$AWS_REGION" || echo "No recent frontend logs found"
}

# Function to destroy infrastructure
destroy() {
    print_warning "This will destroy all AWS resources. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Destroying infrastructure..."
        cd "$TERRAFORM_DIR"
        terraform destroy -auto-approve
        cd - > /dev/null
        print_success "Infrastructure destroyed successfully."
    else
        print_status "Destruction cancelled."
    fi
}

# Function to show help
show_help() {
    echo "DepScan AWS Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  init        Initialize Terraform"
    echo "  plan        Plan Terraform deployment"
    echo "  deploy      Deploy infrastructure and application"
    echo "  push        Build and push Docker images"
    echo "  update      Update ECS services"
    echo "  status      Check deployment status"
    echo "  logs        Show recent application logs"
    echo "  outputs     Show deployment outputs"
    echo "  destroy     Destroy all AWS resources"
    echo "  help        Show this help message"
    echo ""
}

# Main script logic
case "${1:-help}" in
    "init")
        check_prerequisites
        init_terraform
        ;;
    "plan")
        check_prerequisites
        plan_terraform
        ;;
    "deploy")
        check_prerequisites
        init_terraform
        apply_terraform
        get_outputs
        build_and_push
        update_services
        check_status
        print_success "Deployment completed successfully!"
        ;;
    "push")
        check_prerequisites
        build_and_push
        ;;
    "update")
        check_prerequisites
        update_services
        ;;
    "status")
        check_prerequisites
        check_status
        ;;
    "logs")
        check_prerequisites
        show_logs
        ;;
    "outputs")
        check_prerequisites
        get_outputs
        ;;
    "destroy")
        check_prerequisites
        destroy
        ;;
    "help"|*)
        show_help
        ;;
esac