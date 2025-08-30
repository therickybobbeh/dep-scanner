# Outputs for DepScan AWS deployment

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "load_balancer_url" {
  description = "URL to access the application"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
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

# Certificate validation outputs (if using custom domain)
output "certificate_arn" {
  description = "ARN of the SSL certificate"
  value       = var.domain_name != "" && var.certificate_arn == "" ? aws_acm_certificate.main[0].arn : var.certificate_arn
}

output "certificate_validation_records" {
  description = "DNS validation records for SSL certificate"
  value = var.domain_name != "" && var.certificate_arn == "" ? [
    for dvo in aws_acm_certificate.main[0].domain_validation_options : {
      name   = dvo.resource_record_name
      value  = dvo.resource_record_value
      type   = dvo.resource_record_type
      domain = dvo.domain_name
    }
  ] : []
}

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