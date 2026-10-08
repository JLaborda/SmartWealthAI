data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_caller_identity" "current" {}

locals {
  name = var.project_name
}

resource "aws_ecr_repository" "demo" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"
  force_delete         = true # demo-down must remove images with the stack

  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "aws_cloudwatch_log_group" "demo" {
  name              = "/ecs/${local.name}"
  retention_in_days = 1
}

resource "aws_security_group" "demo" {
  name        = "${local.name}-sg"
  description = "Ephemeral CSS FastAPI demo — open ${var.container_port} for create→curl→destroy only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "FastAPI serve (ephemeral demo; no auth)"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${local.name}-sg"
    Purpose = "ephemeral-demo"
  }
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_cluster" "demo" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_ecs_task_definition" "demo" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "serve"
    image     = "${aws_ecr_repository.demo.repository_url}:${var.image_tag}"
    essential = true
    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]
    environment = [{
      name  = "CREDIT_PIPELINE_ARTIFACT"
      value = "/artifact/pipeline.joblib"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.demo.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "serve"
      }
    }
  }])
}

resource "aws_ecs_service" "demo" {
  name            = local.name
  cluster         = aws_ecs_cluster.demo.id
  task_definition = aws_ecs_task_definition.demo.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.demo.id]
    assign_public_ip = true
  }

  # demo-up creates ECR first, pushes :demo, then applies this service.
  depends_on = [aws_iam_role_policy_attachment.ecs_execution]
}