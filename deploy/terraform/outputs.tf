# Outputs for DepScan AWS MVP deployment

output "access_instructions" {
  description = "Instructions for accessing the deployed services"
  value = <<-EOT
    Services deployed with Application Load Balancer:
    
    🌐 **Stable Access URLs:**
    - Frontend: http://${aws_lb.main.dns_name}
    - Backend API: http://${aws_lb.main.dns_name}/api/health
    - API Docs: http://${aws_lb.main.dns_name}/api/docs
    
    ✅ These URLs remain consistent across deployments!
    
    📍 AWS Console Access:
    - ECS Console: https://console.aws.amazon.com/ecs/
    - Load Balancer Console: https://console.aws.amazon.com/ec2/v2/home#LoadBalancers
  EOT
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
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