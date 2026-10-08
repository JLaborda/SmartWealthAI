---
status: accepted
---

# First `platform/` slice: ephemeral Fargate CSS serve

**Decision:** The first shared AWS / Terraform delivery under `platform/` is an **ephemeral demo environment** that runs the existing credit CSS FastAPI (`/health`, `/score`, `/drivers`) on **ECS Fargate + ECR**, with local wrapper scripts for up/down — not the cancelled investing CI/CD M2 lake/OIDC stack, and not a persistent production CSS deployment.

**Why:** Credit domain demos already work locally (chapter 5 scoring, FastAPI, PSI). [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md) and [ADR-0003](0003-phase2-qv-cancelled.md) defer cloud to `platform/` after local demos. Stakeholders want a tangible `apply`/`destroy` story without reopening Phase 2 QV or full OIDC/S3 scope ([#105](https://github.com/JLaborda/SmartWealthAI/issues/105) and related issues remain `wontfix`).

**Trade-offs:**

| Chosen | Rejected (this cut) | Reason |
| --- | --- | --- |
| Fargate + ECR, no ALB, public IP | App Runner / single EC2 | Aligns with portfolio ECS direction; still thin |
| Bake `pipeline.joblib` into a **demo** serve image | S3/EFS artifact mount | No persistent storage; simple destroy |
| Separate demo Dockerfile | Optional COPY in local serve Dockerfile | Keeps volume-mount local path stable |
| Script wrapper (`demo-up` / `demo-down`) | Pure `terraform apply` or GitHub CD | Image build/push must happen; CD is next sprint |
| Default VPC + open SG:8000 | Auth, IP allowlist, TLS | Create → test → destroy only |
| Local Terraform state | Remote state bucket | Avoids bootstrap dependency for a destroyable demo |

**Consequences:**

- Spec: [`credit/docs/features/aws-fargate-serve-demo.md`](../../credit/docs/features/aws-fargate-serve-demo.md)
- Do not add AWS terms to [`credit/CONTEXT.md`](../../credit/CONTEXT.md)
- Future CD/OIDC, ALB/TLS, API keys, and S3 artifact stores are **new** issues — they do not revive investing M2 tickets as written
- Friday MUST rehearsal stays local ([`friday-demo.md`](../../credit/docs/guides/friday-demo.md)); this ADR covers the stretch cloud path only
