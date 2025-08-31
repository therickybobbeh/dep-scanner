# Outputs for DepScan AWS MVP deployment

output "access_instructions" {
  description = "Instructions for accessing the deployed services"
  value = <<-EOT
    Services deployed with direct public access:
    
    1. Go to AWS ECS Console: https://console.aws.amazon.com/ecs/
    2. Click on cluster: ${aws_ecs_cluster.main.name}
    3. Click on Services, then click on a service
    4. Click on Tasks tab, then click on a running task
    5. In the Network section, find the Public IP
    
    Access URLs (replace [PUBLIC_IP] with actual IP):
    - Frontend: http://[PUBLIC_IP]:${var.frontend_port}
    - Backend API: http://[PUBLIC_IP]:${var.backend_port}/health
    - API Docs: http://[PUBLIC_IP]:${var.backend_port}/docs
  EOT
}

output "backend_ecr_repository_url" {
  description = "URL of the backend ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  description = "URL of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "backend_service_name" {
  description = "Name of the backend ECS service"
  value       = aws_ecs_service.backend.name
}

output "frontend_service_name" {
  description = "Name of the frontend ECS service"
  value       = aws_ecs_service.frontend.name
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions IAM role"
  value       = var.github_repo != "" ? aws_iam_role.github_actions[0].arn : null
}

output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secrets.name
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.name
}

# SSL/Certificate outputs removed for MVP (direct HTTP access only)

# Environment variables for GitHub Actions
output "deployment_config" {
  description = "Configuration values for deployment"
  value = {
    aws_region                    = var.aws_region
    backend_ecr_repository        = aws_ecr_repository.backend.name
    frontend_ecr_repository       = aws_ecr_repository.frontend.name
    ecs_cluster_name             = aws_ecs_cluster.main.name
    backend_service_name         = aws_ecs_service.backend.name
    frontend_service_name        = aws_ecs_service.frontend.name
    backend_task_definition      = aws_ecs_task_definition.backend.family
    frontend_task_definition     = aws_ecs_task_definition.frontend.family
  }
  sensitive = false
}