provider "aws" {
  region = var.aws_region
  # Credentials: AWS_PROFILE (required by demo-up/down) or standard AWS env chain.
}