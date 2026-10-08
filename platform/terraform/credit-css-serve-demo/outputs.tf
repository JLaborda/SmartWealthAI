output "aws_region" {
  description = "Region of this stack."
  value       = var.aws_region
}

output "ecr_repository_url" {
  description = "ECR repository URL (tag with :demo after push)."
  value       = aws_ecr_repository.demo.repository_url
}

output "ecr_repository_name" {
  description = "ECR repository name."
  value       = aws_ecr_repository.demo.name
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.demo.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.demo.name
}

output "container_port" {
  description = "Serve port."
  value       = var.container_port
}

output "account_id" {
  description = "AWS account id (debug)."
  value       = data.aws_caller_identity.current.account_id
}