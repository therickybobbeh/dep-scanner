# 🚀 DepScan AWS MVP Deployment Guide

Simple AWS deployment for your DepScan vulnerability scanner using minimal, cost-effective infrastructure.

## 🏗️ MVP Architecture

```
Internet → ECS Fargate Services ← ECR Images
                ↓                    ↑
        AWS Secrets Manager    GitHub Actions
```

**Core Components (MVP):**
- **ECS Fargate**: Serverless containers for backend and frontend
- **ECR**: Private Docker registries for your images  
- **Secrets Manager**: Secure environment variables
- **GitHub Actions**: Automated deployments

## 📋 Prerequisites & Setup

### 1. AWS Account Setup

**Create AWS Account:**
1. Go to [aws.amazon.com](https://aws.amazon.com) and create an account
2. Set up billing alerts (recommended: $10, $50, $100 thresholds)
3. Enable MFA on your root account

**Create IAM User for Deployment:**
```bash
# Create deployment user with programmatic access
aws iam create-user --user-name depscan-deploy
aws iam attach-user-policy --user-name depscan-deploy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam create-access-key --user-name depscan-deploy
```

### 2. Local Development Environment

**Install Required Tools:**

```bash
# macOS with Homebrew
brew install awscli terraform docker

# Ubuntu/Debian
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Install Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip && sudo mv terraform /usr/local/bin/

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
```

**Configure AWS CLI:**
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)

# Verify configuration
aws sts get-caller-identity
```

### 3. GitHub Repository Setup

**Prepare Repository:**
1. Fork or clone this repository
2. Ensure GitHub Actions are enabled in repository settings
3. Prepare to add secrets (we'll do this after infrastructure deployment)

## 🚀 Step-by-Step Deployment

### Step 1: Configure Your Environment

**Create Terraform Configuration:**

Create `deploy/terraform/terraform.tfvars`:

```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars
```

**Edit terraform.tfvars with your values:**

```hcl
# REQUIRED: Basic Configuration
aws_region    = "us-east-1"              # Choose your preferred region
project_name  = "depscan"                # Will prefix all resources
environment   = "mvp"                    # Environment identifier
github_repo   = "yourusername/yourrepo"  # For GitHub Actions OIDC

# OPTIONAL: Resource Sizing (keep small for MVP)
backend_cpu      = 256    # 0.25 vCPU (minimal)
backend_memory   = 512    # 512MB RAM (minimal)
frontend_cpu     = 256    # 0.25 vCPU
frontend_memory  = 512    # 512MB RAM

# OPTIONAL: Tags
tags = {
  Project     = "DepScan"
  Environment = "mvp"
  ManagedBy   = "Terraform"
}
```

### Step 2: Deploy AWS Infrastructure

**Initialize and Deploy:**

```bash
# Navigate to terraform directory
cd deploy/terraform

# Initialize Terraform (downloads providers)
terraform init

# Review what will be created
terraform plan

# Deploy infrastructure (takes 5-10 minutes)
terraform apply
```

**Expected Output:**
```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

Outputs:

backend_service_url = "depscan-mvp-backend.123456789.us-east-1.compute.amazonaws.com:8000"
frontend_service_url = "depscan-mvp-frontend.123456789.us-east-1.compute.amazonaws.com:80"
backend_ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/depscan-mvp-backend"
frontend_ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/depscan-mvp-frontend"
github_actions_role_arn = "arn:aws:iam::123456789012:role/depscan-mvp-github-actions-role"
```

### Step 3: Set Up GitHub Actions

**Copy workflow to your repository:**

```bash
# From project root
mkdir -p .github/workflows
cp deploy/.github/workflows/deploy.yml .github/workflows/
```

**Add GitHub Repository Secret:**

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `AWS_ROLE_ARN`
4. Value: Copy the `github_actions_role_arn` from Terraform output above
5. Click "Add secret"

### Step 4: Initial Deployment

**Push to trigger deployment:**

```bash
git add .github/workflows/deploy.yml
git commit -m "Add GitHub Actions deployment workflow"
git push origin main
```

**Monitor deployment:**
- Go to your GitHub repository → Actions tab
- Watch the "Deploy to AWS ECS" workflow run
- First deployment takes ~10-15 minutes (building and pushing containers)

### Step 5: Access Your Application

**Get your service URLs:**

```bash
cd deploy/terraform
terraform output backend_service_url
terraform output frontend_service_url
```

**Test the deployment:**
```bash
# Check backend health
curl http://your-backend-url:8000/health

# Check frontend (should return HTML)
curl http://your-frontend-url:80/
```

## File Structure

```
deploy/
├── terraform/           # Infrastructure as Code
│   ├── main.tf         # Main Terraform configuration
│   ├── variables.tf    # Input variables
│   ├── outputs.tf      # Output values
│   ├── networking.tf   # VPC, Security Groups
│   ├── alb.tf         # Load Balancer, SSL, DNS
│   ├── ecs.tf         # ECS Cluster, Services, Tasks
│   └── security.tf    # IAM roles, Secrets Manager
├── docker/             # Docker configurations
│   ├── Dockerfile.backend   # Production backend image
│   ├── Dockerfile.frontend  # Production frontend image
│   └── nginx.conf          # Nginx configuration for frontend
├── .github/workflows/  # GitHub Actions
│   └── deploy.yml     # CI/CD pipeline
├── scripts/           # Deployment utilities
│   └── deploy.sh     # Management script
└── README.md         # This file
```

## Management Commands

The `deploy.sh` script provides several commands:

```bash
# Initialize Terraform
./deploy/scripts/deploy.sh init

# Plan changes
./deploy/scripts/deploy.sh plan

# Full deployment
./deploy/scripts/deploy.sh deploy

# Build and push images
./deploy/scripts/deploy.sh push

# Update ECS services
./deploy/scripts/deploy.sh update

# Check status
./deploy/scripts/deploy.sh status

# View logs
./deploy/scripts/deploy.sh logs

# Show outputs
./deploy/scripts/deploy.sh outputs

# Destroy everything
./deploy/scripts/deploy.sh destroy
```

## Custom Domain Setup

To use a custom domain:

1. Set `domain_name` in `terraform.tfvars`
2. Ensure your domain is managed by Route 53
3. Deploy with Terraform
4. Add DNS validation records for SSL certificate (if not using existing cert)

## GitHub Actions Setup

### Prerequisites

1. Set `github_repo` in `terraform.tfvars`
2. Deploy infrastructure to create OIDC provider and role
3. Add secrets to GitHub repository:
   - `AWS_ROLE_ARN`: Get from `./deploy/scripts/deploy.sh outputs`

### Workflow

The GitHub Actions workflow:
1. Runs tests for both backend and frontend
2. Builds and pushes Docker images to ECR
3. Updates ECS services with new images
4. Includes automatic rollback on failure

## Security

- Uses least-privilege IAM roles
- Secrets stored in AWS Secrets Manager
- Security groups restrict network access
- Container images scanned for vulnerabilities
- HTTPS/SSL termination at load balancer

## Monitoring

- CloudWatch logs for all services
- ECS service health checks
- Load balancer health checks
- Container-level health checks

## 💰 MVP Cost Optimization

Minimal AWS setup for testing and small-scale use:
- **ECS Fargate**: 0.25 vCPU, 512MB RAM per service
- **ECR**: Private image repositories
- **Secrets Manager**: Environment variable storage

**Estimated monthly cost (us-east-1):**
- ECS Fargate (2 small services): ~$15-25/month
- ECR storage: ~$1/month  
- Secrets Manager: ~$1/month
- **Total: ~$17-27/month** 📉

## Scaling

To handle more traffic:

1. **Horizontal scaling**: Increase `desired_count` in variables
2. **Vertical scaling**: Increase CPU/memory in variables
3. **Auto-scaling**: Add ECS auto-scaling policies
4. **Multi-AZ**: Deploy across multiple availability zones

## 🛠️ Troubleshooting Guide

### Common Issues & Solutions

#### 1. **Terraform Apply Fails**

**Error: "Access Denied" or "UnauthorizedOperation"**
```bash
# Check AWS credentials are configured correctly
aws sts get-caller-identity

# Ensure user has sufficient permissions
aws iam list-attached-user-policies --user-name depscan-deploy
```

**Error: "Resource already exists"**
```bash
# Import existing resources (if any)
terraform import aws_vpc.main vpc-12345678

# Or destroy and recreate
terraform destroy
terraform apply
```

#### 2. **ECS Tasks Failing to Start**

**Check task definition and logs:**
```bash
# Get cluster info
aws ecs describe-clusters --clusters depscan-prod-cluster

# Check service status
aws ecs describe-services --cluster depscan-prod-cluster --services depscan-prod-backend depscan-prod-frontend

# View task logs
aws logs get-log-events --log-group-name /ecs/depscan-prod-backend --log-stream-name ecs/backend/[TASK-ID]
```

**Common causes:**
- Container image not found in ECR
- Insufficient memory allocation
- Health check failing
- Missing environment variables

#### 3. **GitHub Actions Deployment Failing**

**Error: "Unable to assume role"**
```bash
# Verify role ARN is correct in GitHub secrets
aws iam get-role --role-name depscan-prod-github-actions-role

# Check trust policy allows GitHub OIDC
aws iam get-role --role-name depscan-prod-github-actions-role --query 'Role.AssumeRolePolicyDocument'
```

**Error: "ECR login failed"**
```bash
# Test ECR login manually
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [ECR-URI]
```

#### 4. **Services Not Accessible**

**Check ECS service status:**
```bash
# Get service details
aws ecs describe-services --cluster depscan-mvp-cluster --services depscan-mvp-backend depscan-mvp-frontend

# Check if tasks are running
aws ecs list-tasks --cluster depscan-mvp-cluster --service-name depscan-mvp-backend

# Get public IP (if using public subnets)
aws ecs describe-tasks --cluster depscan-mvp-cluster --tasks [TASK-ARN] --query 'tasks[0].attachments[0].details'
```

### 📊 Monitoring & Health Checks

**View Application Logs:**
```bash
# Backend logs (if CloudWatch enabled)
aws logs tail /ecs/depscan-mvp-backend --follow

# Frontend logs (if CloudWatch enabled)  
aws logs tail /ecs/depscan-mvp-frontend --follow

# Or check ECS console for basic logs
```

**Health Check Endpoints:**
```bash
# Backend health (use your service URL)
curl http://your-backend-service:8000/health

# Test scan functionality
curl -X POST http://your-backend-service:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"manifest_files": {"package.json": "test"}}'
```

### 🔧 MVP Scaling (When Needed)

**Scale Services (if you get more traffic):**
```bash
# Increase backend instances
aws ecs update-service \
  --cluster depscan-mvp-cluster \
  --service depscan-mvp-backend \
  --desired-count 2

# Check service status
aws ecs describe-services --cluster depscan-mvp-cluster --services depscan-mvp-backend
```

## Cleanup

To remove all AWS resources:

```bash
./deploy/scripts/deploy.sh destroy
```

**Warning**: This will permanently delete all resources and data.

## Development vs Production

This configuration is set up for production use. For development:

1. Use smaller instance sizes
2. Consider using EC2 instead of Fargate
3. Use development-specific tags
4. Consider single-container deployments

## Support

For issues with this deployment setup:
1. Check the troubleshooting section above
2. Review AWS CloudWatch logs
3. Check ECS service health in AWS Console