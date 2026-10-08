# Ephemeral CSS FastAPI on AWS (operator)

**Ephemeral demo environment only — not production.** Create → curl fixtures → destroy. No ALB, no TLS, no auth, no S3 lake, no GitHub CD.

Spec: [`../../credit/docs/features/aws-fargate-serve-demo.md`](../../credit/docs/features/aws-fargate-serve-demo.md) · ADR: [`../../docs/adr/0004-platform-ephemeral-fargate-serve.md`](../../docs/adr/0004-platform-ephemeral-fargate-serve.md) · Friday MUST stays local: [`../../credit/docs/guides/friday-demo.md`](../../credit/docs/guides/friday-demo.md)

## Prerequisites

- Poetry env at repo root (`poetry install`)
- Docker (build + push)
- Terraform ≥ 1.5
- AWS CLI v2 with a profile that can manage ECR, ECS, IAM roles, EC2 SG/ENI, CloudWatch Logs in the target account
- A **default VPC** with public subnets in the region (script uses `assign_public_ip`)

```bash
export AWS_PROFILE=your-demo-profile   # required
export AWS_REGION=eu-west-1            # optional; default eu-west-1
```

## Up

From repo root:

```bash
./platform/scripts/demo-up.sh
```

What it does:

1. Hermetic fit → `credit/demo_artifact/pipeline.joblib` (`prepare-serve-demo-artifact.sh`, #173)
2. `terraform apply` for ECR (local state under `platform/terraform/credit-css-serve-demo/`)
3. `docker build -f credit/Dockerfile.serve.demo` and push `:demo` to that ECR
4. Full apply: ECS Fargate service (256 CPU / 512 MB, desired count 1, SG open on 8000, public IP, no ALB)
5. Prints the public base URL and example curls

Example (after up prints `http://A.B.C.D:8000`):

```bash
curl -s http://A.B.C.D:8000/health
curl -s http://A.B.C.D:8000/score \
  -H 'content-type: application/json' \
  -d @tests/credit/fixtures/serving/score_request.json
curl -s http://A.B.C.D:8000/drivers \
  -H 'content-type: application/json' \
  -d @tests/credit/fixtures/serving/drivers_request.json
```

## Down

```bash
./platform/scripts/demo-down.sh
```

Runs `terraform destroy` with the same profile/region. The ECR repository uses `force_delete = true`, so images go away with the stack. Local `*.tfstate` is updated on this machine — run up/down from the same checkout (or copy state) if you switch hosts.

## Honest limits

- Unauthenticated `0.0.0.0/0:8000` for a short window only — destroy when finished
- Local Terraform state (no remote backend) by design
- Does not replace the Friday local rehearsal path
- Never run `terraform apply` / `demo-up` from CI

## Cheap checks (no AWS apply)

```bash
make platform-tf-check
```

Runs `terraform fmt -check` and `terraform validate` (providers download; no credentials required for validate).