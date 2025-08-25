#!/bin/bash

# AWS Deployment Script for DepScan
# This script deploys DepScan to AWS using Docker and optionally sets up ALB

set -e

# Configuration
APP_NAME="dep-scanner"
DOCKER_IMAGE_NAME="dep-scanner"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-prod}"

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

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_info "All requirements met."
}

build_image() {
    log_info "Building Docker image..."
    
    # Navigate to project root
    cd "$(dirname "$0")/../.."
    
    # Build production image
    docker build -f Dockerfile.aws -t ${DOCKER_IMAGE_NAME}:${ENVIRONMENT} .
    
    # Tag for AWS ECR if ECR_REPOSITORY is set
    if [[ -n "${ECR_REPOSITORY}" ]]; then
        docker tag ${DOCKER_IMAGE_NAME}:${ENVIRONMENT} ${ECR_REPOSITORY}:${ENVIRONMENT}
        docker tag ${DOCKER_IMAGE_NAME}:${ENVIRONMENT} ${ECR_REPOSITORY}:latest
    fi
    
    log_info "Docker image built successfully."
}

push_to_ecr() {
    if [[ -z "${ECR_REPOSITORY}" ]]; then
        log_warn "ECR_REPOSITORY not set, skipping ECR push."
        return
    fi
    
    log_info "Pushing image to ECR..."
    
    # Get ECR login token
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY}
    
    # Push images
    docker push ${ECR_REPOSITORY}:${ENVIRONMENT}
    docker push ${ECR_REPOSITORY}:latest
    
    log_info "Image pushed to ECR successfully."
}

deploy_ecs() {
    if [[ -z "${ECS_CLUSTER}" ]] || [[ -z "${ECS_SERVICE}" ]]; then
        log_warn "ECS_CLUSTER or ECS_SERVICE not set, skipping ECS deployment."
        return
    fi
    
    log_info "Deploying to ECS..."
    
    # Update ECS service
    aws ecs update-service \
        --region ${AWS_REGION} \
        --cluster ${ECS_CLUSTER} \
        --service ${ECS_SERVICE} \
        --force-new-deployment
    
    # Wait for deployment to complete
    log_info "Waiting for deployment to complete..."
    aws ecs wait services-stable \
        --region ${AWS_REGION} \
        --cluster ${ECS_CLUSTER} \
        --services ${ECS_SERVICE}
    
    log_info "ECS deployment completed successfully."
}

deploy_docker_compose() {
    log_info "Deploying with Docker Compose..."
    
    cd "$(dirname "$0")"
    
    # Stop existing containers
    docker-compose -f docker-compose.prod.yml down
    
    # Start new containers
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for health check
    log_info "Waiting for application to be healthy..."
    sleep 30
    
    # Check health
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_info "Application is healthy!"
    else
        log_error "Application health check failed!"
        docker-compose -f docker-compose.prod.yml logs
        exit 1
    fi
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove dangling images
    docker image prune -f
    
    log_info "Cleanup completed."
}

main() {
    log_info "Starting DepScan AWS deployment..."
    
    check_requirements
    build_image
    
    # Choose deployment method based on environment variables
    if [[ -n "${ECR_REPOSITORY}" ]]; then
        push_to_ecr
        
        if [[ -n "${ECS_CLUSTER}" ]] && [[ -n "${ECS_SERVICE}" ]]; then
            deploy_ecs
        else
            log_info "ECR push completed. Deploy manually to your chosen AWS service."
        fi
    else
        deploy_docker_compose
    fi
    
    cleanup
    
    log_info "Deployment completed successfully!"
}

# Help message
show_help() {
    cat << EOF
AWS Deployment Script for DepScan

Usage: $0 [options]

Environment Variables:
  AWS_REGION          AWS region (default: us-east-1)
  ENVIRONMENT         Deployment environment (default: prod)
  ECR_REPOSITORY      ECR repository URI (optional)
  ECS_CLUSTER         ECS cluster name (optional)
  ECS_SERVICE         ECS service name (optional)

Examples:
  # Simple Docker Compose deployment
  ./deploy.sh

  # ECR deployment
  ECR_REPOSITORY=123456789.dkr.ecr.us-east-1.amazonaws.com/dep-scanner ./deploy.sh

  # Full ECS deployment
  ECR_REPOSITORY=123456789.dkr.ecr.us-east-1.amazonaws.com/dep-scanner \\
  ECS_CLUSTER=my-cluster \\
  ECS_SERVICE=dep-scanner-service \\
  ./deploy.sh

Options:
  -h, --help    Show this help message

EOF
}

# Parse command line arguments
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac