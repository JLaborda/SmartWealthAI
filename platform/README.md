# Platform

Shared AWS / Terraform and operator scripts. Domain language stays in `credit/` and investing docs — see [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) and [ADR-0004](../docs/adr/0004-platform-ephemeral-fargate-serve.md).

## Scripts (credit CSS serve demo)

| Script | Purpose |
| --- | --- |
| `scripts/prepare-serve-demo-artifact.sh` | Hermetic fit → `credit/demo_artifact/pipeline.joblib` for `credit/Dockerfile.serve.demo` (#173) |
| `scripts/demo-up.sh` | Prepare → bake/push → Terraform apply → print public curl URL (#174) |
| `scripts/demo-down.sh` | `terraform destroy` including ECR images (#174) |

## Terraform

| Path | Purpose |
| --- | --- |
| `terraform/credit-css-serve-demo/` | ECR + ECS Fargate (default VPC, public IP, no ALB, local state) |

Operator guide: [`docs/ephemeral-css-serve-demo.md`](docs/ephemeral-css-serve-demo.md).

```bash
export AWS_PROFILE=your-demo-profile
./platform/scripts/demo-up.sh
# … curl /health /score /drivers …
./platform/scripts/demo-down.sh
```

`make platform-tf-check` — `fmt` + `validate` only (no apply).