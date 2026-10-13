#!/usr/bin/env bash
# Ephemeral CSS FastAPI on ECS Fargate: prepare → bake → push → apply → print curls.
# Requires AWS_PROFILE. Never run from CI. Spec: credit/docs/features/aws-fargate-serve-demo.md (#174).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TF_DIR="$ROOT/platform/terraform/credit-css-serve-demo"
IMAGE_TAG="${IMAGE_TAG:-demo}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
export AWS_REGION
export AWS_DEFAULT_REGION="$AWS_REGION"

die() { echo "error: $*" >&2; exit 1; }

[[ -n "${AWS_PROFILE:-}" ]] || die "AWS_PROFILE is required (e.g. export AWS_PROFILE=my-demo)"
command -v terraform >/dev/null || die "terraform not found"
command -v aws >/dev/null || die "aws CLI not found"
command -v docker >/dev/null || die "docker not found"
command -v poetry >/dev/null || die "poetry not found"

echo "==> AWS identity (profile=$AWS_PROFILE region=$AWS_REGION)"
aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null

echo "==> Prepare hermetic serve-demo artifact (#173)"
"$ROOT/platform/scripts/prepare-serve-demo-artifact.sh"

echo "==> Terraform init ($TF_DIR)"
cd "$TF_DIR"
terraform init -input=false

echo "==> Ensure ECR exists (push before Fargate tasks start)"
terraform apply -input=false -auto-approve \
  -var="aws_region=$AWS_REGION" \
  -var="image_tag=$IMAGE_TAG" \
  -target=aws_ecr_repository.demo

ECR_URL="$(terraform output -raw ecr_repository_url)"
echo "==> ECR: $ECR_URL"

echo "==> Docker build + push ($IMAGE_TAG)"
cd "$ROOT"
aws ecr get-login-password --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  | docker login --username AWS --password-stdin "$(echo "$ECR_URL" | cut -d/ -f1)"

docker build -f credit/Dockerfile.serve.demo -t "credit-css-serve-demo:$IMAGE_TAG" .
docker tag "credit-css-serve-demo:$IMAGE_TAG" "$ECR_URL:$IMAGE_TAG"
docker push "$ECR_URL:$IMAGE_TAG"

echo "==> Terraform apply (ECS Fargate service)"
cd "$TF_DIR"
terraform apply -input=false -auto-approve \
  -var="aws_region=$AWS_REGION" \
  -var="image_tag=$IMAGE_TAG"

CLUSTER="$(terraform output -raw ecs_cluster_name)"
SERVICE="$(terraform output -raw ecs_service_name)"
PORT="$(terraform output -raw container_port)"

echo "==> Force new deployment and wait for service stable"
aws ecs update-service \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --output text >/dev/null

aws ecs wait services-stable \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER" \
  --services "$SERVICE"

echo "==> Resolve task public IP"
TASK_ARN="$(
  aws ecs list-tasks \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --cluster "$CLUSTER" \
    --service-name "$SERVICE" \
    --desired-status RUNNING \
    --query 'taskArns[0]' \
    --output text
)"
[[ -n "$TASK_ARN" && "$TASK_ARN" != "None" ]] || die "no RUNNING task found"

ENI_ID="$(
  aws ecs describe-tasks \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --cluster "$CLUSTER" \
    --tasks "$TASK_ARN" \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value | [0]' \
    --output text
)"
[[ -n "$ENI_ID" && "$ENI_ID" != "None" ]] || die "could not resolve ENI for task"

PUBLIC_IP="$(
  aws ec2 describe-network-interfaces \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --network-interface-ids "$ENI_ID" \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text
)"
[[ -n "$PUBLIC_IP" && "$PUBLIC_IP" != "None" ]] || die "task has no public IP (check assign_public_ip / subnet)"

BASE="http://${PUBLIC_IP}:${PORT}"
echo
echo "Ephemeral demo URL (not production): $BASE"
echo "Try:"
echo "  curl -s $BASE/health"
echo "  curl -s $BASE/score -H 'content-type: application/json' -d @$ROOT/tests/credit/fixtures/serving/score_request.json"
echo "  curl -s $BASE/drivers -H 'content-type: application/json' -d @$ROOT/tests/credit/fixtures/serving/drivers_request.json"
echo
echo "Tear down when done: AWS_PROFILE=$AWS_PROFILE AWS_REGION=$AWS_REGION ./platform/scripts/demo-down.sh"
echo "$BASE" >"$TF_DIR/.last_demo_url"
echo "$BASE"