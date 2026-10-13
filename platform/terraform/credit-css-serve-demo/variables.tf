variable "aws_region" {
  description = "AWS region for the ephemeral CSS serve demo stack."
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Name prefix for demo resources."
  type        = string
  default     = "credit-css-serve-demo"
}

variable "image_tag" {
  description = "ECR image tag pushed by demo-up (task definition uses repository_url:tag)."
  type        = string
  default     = "demo"
}

variable "container_port" {
  description = "Container / host port for the FastAPI serve demos."
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "ECS service desired count."
  type        = number
  default     = 1
}