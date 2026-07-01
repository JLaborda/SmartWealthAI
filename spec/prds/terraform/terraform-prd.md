# PRD: Terraform AWS Infrastructure (M2)

**Status:** Ready for implementation  
**Parent PRD:** [`spec/prds/ci-cd/ci-cd-prd.md`](../ci-cd/ci-cd-prd.md) (milestone M2)  
**Feature spec:** [`spec/features/014-cicd-infrastructure/spec.md`](../../features/014-cicd-infrastructure/spec.md)  
**ADR:** [`spec/adr/0003-terraform-for-aws-iac.md`](../../adr/0003-terraform-for-aws-iac.md)  
**GitHub epic:** [#105](https://github.com/JLaborda/SmartWealthAI/issues/105)

---

## Problem Statement

SmartWealthAI needs reproducible AWS infrastructure (S3 data lake, GitHub OIDC IAM, Secrets Manager) but has no IaC in the repo. M2 Terraform unblocks ingest-smoke without provisioning empty ECS before the pipeline Docker image exists (M3).

## Solution

Terraform v1 scoped to **CI/CD milestone M2**: bootstrap remote state, dev/prod S3 buckets, GitHub OIDC roles, Secrets Manager placeholder for `SIMFIN_API_KEY`. ECR/ECS/MLflow deferred to M3–M6.

## Implementation decisions

| Topic | Decision |
| --- | --- |
| v1 scope | M2 only — S3 dev+prod, OIDC IAM, Secrets Manager skeleton |
| Tool | Terraform (`infra/terraform/`) |
| State | S3 + DynamoDB (bootstrap module, one-time manual apply) |
| Accounts | Single AWS account; dev/prod isolated by bucket + IAM role |
| OIDC | Repo `JLaborda/SmartWealthAI`; dev = `develop` + Environment `dev`; prod = `main` + Environment `production` |
| Apply | `workflow_dispatch` only; prod requires GitHub Environment approval |
| Out of v1 | ECR, ECS, EC2, EventBridge; application `LAKE_URI`/boto3 ([#112](https://github.com/JLaborda/SmartWealthAI/issues/112)) |

## User stories (M2)

1. As a developer, I want Terraform remote state in S3 with DynamoDB locking, so that infra changes are collaborative and auditable.
2. As a developer, I want separate dev and prod S3 data lake buckets with versioning and encryption, so that test data never mixes with production.
3. As a developer, I want GitHub Actions to assume AWS roles via OIDC (no static keys), so that CI secrets stay minimal.
4. As a developer, I want dev and prod OIDC roles with least-privilege S3 policies, so that a dev workflow cannot write prod buckets.
5. As a developer, I want `SIMFIN_API_KEY` in Secrets Manager (placeholder at apply time), so that runtime tasks can read keys without repo commits.
6. As a developer, I want `terraform fmt -check`, `validate`, and `plan` on PRs touching `infra/terraform/`, so that infra drift is caught in review.
7. As a developer, I want a manual apply workflow with prod approval gate, so that production promotion is deliberate.
8. As a developer, I want an ingest-smoke workflow (OIDC → dev S3 write) after M2 apply, so that AWS integration is proven outside PR CI.

## Vertical slices (GitHub issues)

| Issue | Slice |
| --- | --- |
| [#106](https://github.com/JLaborda/SmartWealthAI/issues/106) | Bootstrap: remote state bucket + DynamoDB lock |
| [#107](https://github.com/JLaborda/SmartWealthAI/issues/107) | Storage module: dev/prod S3 buckets |
| [#108](https://github.com/JLaborda/SmartWealthAI/issues/108) | IAM: GitHub OIDC provider + dev/prod roles |
| [#109](https://github.com/JLaborda/SmartWealthAI/issues/109) | Secrets Manager: SimFin API key placeholder |
| [#110](https://github.com/JLaborda/SmartWealthAI/issues/110) | Terraform CI workflow: fmt, validate, plan |
| [#111](https://github.com/JLaborda/SmartWealthAI/issues/111) | Ingest-smoke workflow: OIDC auth + dev S3 write |
| [#112](https://github.com/JLaborda/SmartWealthAI/issues/112) | Application: `LAKE_URI` config + S3 lake I/O |

## Testing

- **PR CI:** `terraform fmt -check`, `validate`, `plan` — no live `apply` on merge.
- **Post-apply:** ingest-smoke workflow proves OIDC → dev S3 write.
- **Hermetic:** application S3 tests use local temp dirs or moto; no live AWS in PR CI.

## Out of scope

Multi-account AWS, OpenTofu, Terraform Cloud, auto-apply on merge, ECS/ECR/EC2 in v1.
