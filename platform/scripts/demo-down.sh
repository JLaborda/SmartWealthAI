#!/usr/bin/env bash
# Destroy ephemeral CSS FastAPI Fargate stack (including ECR images via force_delete).
# Requires AWS_PROFILE. Spec: credit/docs/features/aws-fargate-serve-demo.md (#174).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TF_DIR="$ROOT/platform/terraform/credit-css-serve-demo"
AWS_REGION="${AWS_REGION:-eu-west-1}"
export AWS_REGION
export AWS_DEFAULT_REGION="$AWS_REGION"

die() { echo "error: $*" >&2; exit 1; }

[[ -n "${AWS_PROFILE:-}" ]] || die "AWS_PROFILE is required (e.g. export AWS_PROFILE=my-demo)"
command -v terraform >/dev/null || die "terraform not found"
command -v aws >/dev/null || die "aws CLI not found"

[[ -d "$TF_DIR" ]] || die "missing $TF_DIR"
cd "$TF_DIR"

if [[ ! -f terraform.tfstate ]] && [[ ! -d .terraform ]]; then
  die "no local Terraform state under $TF_DIR — nothing to destroy (run demo-up from this machine first)"
fi

echo "==> AWS identity (profile=$AWS_PROFILE region=$AWS_REGION)"
aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null

echo "==> Terraform init + destroy (ECR force_delete removes images)"
terraform init -input=false
terraform destroy -input=false -auto-approve \
  -var="aws_region=$AWS_REGION"

rm -f "$TF_DIR/.last_demo_url"
echo "==> Stack destroyed (including ECR repository/images)."
