---
status: accepted
---

# Terraform for AWS infrastructure (M2)

SmartWealthAI needs versioned, reproducible AWS resources (S3 data lake, GitHub OIDC IAM, Secrets Manager) before ingest-smoke and cloud pipeline deploys. Manual console setup does not scale across dev/prod or survive team handoff.

## Decision

Use **Terraform** under `infra/terraform/` as the sole infrastructure-as-code tool for **CI/CD milestone M2**:

- Bootstrap module: S3 remote state bucket + DynamoDB lock table (one-time manual apply, local bootstrap state).
- Environment roots: `environments/dev` and `environments/prod` composing storage, IAM (GitHub OIDC), and Secrets Manager modules.
- **Apply via `workflow_dispatch` only** — no auto-apply on merge. Prod requires GitHub Environment `production` approval.
- **Single AWS account**; dev/prod isolated by bucket name and IAM role trust policies.

ECR, ECS, EC2, EventBridge, and MLflow server provisioning are **deferred to M3–M6** per [`spec/prds/ci-cd/ci-cd-prd.md`](../prds/ci-cd/ci-cd-prd.md).

## Considered

| Option | Why not (for M2) |
| --- | --- |
| AWS CDK | Heavier bootstrap; team already aligned on HCL for ops handoff |
| Manual console | Not reproducible; blocks PR review of infra changes |
| OpenTofu / Terraform Cloud | Out of scope for v1; S3 backend is sufficient |
| CDK + Terraform mix | Two IaC tools increase cognitive load |

## Consequences

- Feature spec [`spec/features/014-cicd-infrastructure/spec.md`](../features/014-cicd-infrastructure/spec.md) owns acceptance criteria for M2 slices.
- PRD [`spec/prds/terraform/terraform-prd.md`](../prds/terraform/terraform-prd.md) captures user stories and vertical slices ([#105](https://github.com/JLaborda/SmartWealthAI/issues/105)–[#112](https://github.com/JLaborda/SmartWealthAI/issues/112)).
- Application `LAKE_URI` / boto3 lake I/O is a **separate code slice** ([#112](https://github.com/JLaborda/SmartWealthAI/issues/112)), not Terraform scope.
- Operators run bootstrap once; child environments use remote backend outputs documented in `infra/terraform/bootstrap/README.md`.
