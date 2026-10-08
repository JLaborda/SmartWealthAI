# Feature: Ephemeral CSS FastAPI serve on AWS (Fargate)

**Status:** in progress — docs (#172) + bake-image (#173) done; **#174 Terraform + demo-up/down in PR** (HITL apply/curl/destroy needs Jorge’s `AWS_PROFILE`)  
**GitHub:** parent [#171](https://github.com/JLaborda/SmartWealthAI/issues/171) · [#172](https://github.com/JLaborda/SmartWealthAI/issues/172) docs · [#173](https://github.com/JLaborda/SmartWealthAI/issues/173) bake-image · [#174](https://github.com/JLaborda/SmartWealthAI/issues/174) AWS up/down  
**Domain:** credit / CSS (demo surface) + shared `platform/` (IaC)  
**Glossary:** [`../../CONTEXT.md`](../../CONTEXT.md) (domain only — no AWS terms) · Map: [`../../../CONTEXT-MAP.md`](../../../CONTEXT-MAP.md)  
**Related:** chapter 5 [`css-chapter5-mart-and-scoring.md`](css-chapter5-mart-and-scoring.md) · PSI [`psi-data-drift.md`](psi-data-drift.md) · Friday MUST [`../guides/friday-demo.md`](../guides/friday-demo.md) · [ADR-0004](../../../docs/adr/0004-platform-ephemeral-fargate-serve.md) · bake guide [`../guides/serve-fastapi.md`](../guides/serve-fastapi.md) · operator [`../../../platform/docs/ephemeral-css-serve-demo.md`](../../../platform/docs/ephemeral-css-serve-demo.md)  
**Code:** `credit/demo_serve_artifact.py`, `credit/Dockerfile.serve.demo`, `platform/scripts/prepare-serve-demo-artifact.sh`, `platform/terraform/credit-css-serve-demo/`, `platform/scripts/demo-up.sh`, `platform/scripts/demo-down.sh` · Tests: `tests/credit/test_serve_demo_bake.py` (API seam); live up/curl/down = HITL

## Problem Statement

The Friday MUST path is local (mart → fit → FastAPI → PSI). Stakeholders also want a tangible **ephemeral cloud** story: stand up the same CSS scoring API on AWS with a simple up/down ritual, then tear it down so nothing persistent (and no surprise cost) remains. Prior investing Terraform/OIDC issues (#105 and Phase 2 ECS) were cancelled (`wontfix`); this is a **new, thinner** first `platform/` slice aimed at credit serve only.

## Solution

Deliver an **ephemeral demo environment** (not production CSS):

1. Operator runs `demo-up` with `AWS_PROFILE`: hermetic fit → bake `pipeline.joblib` into a **dedicated** serve-demo image → Terraform creates ECR + ECS Fargate (public IP, no ALB) → push image → print curl URL.
2. Operator curls `/health`, `/score`, `/drivers` with existing serving fixtures.
3. Operator runs `demo-down` → `terraform destroy` (including ECR images).

No S3 data lake, no auth, no GitHub CD in this cut.

## User Stories

1. As a portfolio owner, I want a one-command cloud up for the CSS FastAPI, so that I can show ranking + drivers on a public URL during a short demo.
2. As a portfolio owner, I want a one-command destroy, so that the demo leaves no lingering AWS cost or open endpoint.
3. As a demo operator, I want the up script to fit from hermetic fixtures and bake the joblib into the image, so that Fargate needs no volume mounts or S3 artifacts.
4. As a demo operator, I want the script to print a ready-to-run curl against the task public IP, so that I do not dig through the ECS console.
5. As a developer, I want Terraform under `platform/`, so that shared infra stays out of the credit domain package.
6. As a developer, I want a separate `Dockerfile.serve.demo` from the volume-mount serve image, so that local Docker docs keep working unchanged.
7. As a risk stakeholder, I want the API contract unchanged (`/health`, `/score`, `/drivers`, same joblib semantics), so that cloud is only a hosting story.
8. As an operator, I want to use `AWS_PROFILE` and a configurable region (default `eu-west-1`), so that the wrong account is harder to hit by accident.
9. As an operator, I want local Terraform state for this stack, so that destroy does not depend on a remote state bucket.
10. As a maintainer, I want this work documented as stretch vs the Friday MUST guide, so that local rehearsal stays the default path.
11. As a maintainer, I want an ADR for the first `platform/` delivery shape, so that future CD/OIDC work does not silently reopen cancelled investing M2 scope.
12. As a security-conscious operator, I accept an unauthenticated public SG for a create→test→destroy window only, so that this sprint stays small.
13. As a future sprint owner, I want CD/OIDC, ALB/TLS, and API keys explicitly out of scope here, so that the next increment has a clear backlog edge.
14. As a CI owner, I want existing hermetic FastAPI tests to remain the model/API seam, so that PRs do not require live `terraform apply`.
15. As a demo operator, I want acceptance to be up → curl fixtures → down, so that “works” means the external behaviour, not HCL unit tests.

## Implementation Decisions

| Topic | Decision |
| --- | --- |
| Surface | FastAPI CSS serve only (same artifact semantics as local `credit-css-serve`) |
| Compute | ECS Fargate + ECR; no ALB; `assign_public_ip` |
| Persistence | No S3 for marts/artifacts/reports; ECR only until destroy |
| Operator UX | Wrapper scripts (`demo-up` / `demo-down`), not “terraform alone” and not GitHub CD |
| Network | Default VPC + new security group `0.0.0.0/0:8000` |
| Auth | None for this ephemeral window |
| Credentials | `AWS_PROFILE` + region variable (default `eu-west-1`); local TF state |
| Image | Dedicated bake image (`Dockerfile.serve.demo`); local volume-mount serve image unchanged |
| Artifact source | Hermetic fit (same fixtures as Friday demo / serving tests) written under a gitignored demo artifact dir |
| Task size | 256 CPU / 512 MB, desired count 1 |
| Repo layout | IaC + scripts in `platform/`; product spec in `credit/docs/features/` |
| Relation to #105 | New issue; does **not** reopen investing lake/OIDC Terraform |

## Testing Decisions

**Primary seam (one):** operator `demo-up` → HTTP `/health` + `/score` + `/drivers` with existing serving fixture JSON → `demo-down`. Assert external behaviour only (reachable URL, successful JSON responses, stack gone after destroy).

**Prior art:** `tests/credit/test_api_serving.py` and friday-demo / serve-fastapi guides cover the API contract hermetically. Do **not** re-test WOE/XGB in this feature.

**CI:** no live `terraform apply` on PR (credentials + cost). Optional later: `terraform fmt` / `validate` only if cheap to add; not required to call this slice done.

## Acceptance criteria

- [x] Feature spec + ADR-0004 + friday-demo stretch link exist in English (#172)
- [x] Bake-image local path: `prepare-serve-demo-artifact` + `Dockerfile.serve.demo` + hermetic pytest + documented docker smoke without volume (#173)
- [x] Terraform under `platform/terraform/credit-css-serve-demo/` + `demo-up.sh` / `demo-down.sh` + operator docs (code path for #174; live apply deferred to HITL)
- [ ] With a valid `AWS_PROFILE`, `demo-up` yields reachable `/health` and successful `/score` + `/drivers` using existing serving fixtures (#174 HITL)
- [ ] `demo-down` destroys the stack including ECR images (#174 HITL)
- [x] Local volume-mount serve Docker path remains documented and unchanged in behaviour
- [x] No AWS vocabulary added to `credit/CONTEXT.md`

## Out of Scope

- S3 lakes, ALB, TLS, API keys, custom VPC (unless default VPC is missing)
- GitHub OIDC / CD on PR or merge
- Batch `score`, fit, or PSI on AWS
- MLflow server, Cognito, multi-environment promotion
- Changes to CSS FastAPI Python handlers
- Reopening cancelled investing Phase 2 / M2 Terraform issues as-is

## Further Notes

Call this an **ephemeral demo environment** in operator docs — not “production.” CSS domain language (credit score, rank-only, risk drivers, PSI) stays in `credit/CONTEXT.md`; hosting belongs to `platform/` + this feature spec.
