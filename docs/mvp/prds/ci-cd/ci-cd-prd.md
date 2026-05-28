# PRD: CI/CD and MLOps Infrastructure (Phase 0)

**Status:** Ready for implementation  
**Canonical architecture:** `docs/mvp/architecture/architecture.md`  
**Related specs:** ETL + data lake, permanent loss filter, backtesting, sell-watch (pipeline vertical slice)

---

## Problem Statement

SmartWealthAI is a portfolio-grade quantitative value-investing MVP that must demonstrate MLOps competence on AWS: reproducible builds, automated quality gates, containerized pipeline execution, and a clear path from development to production. Today the repository has Poetry dependencies and a development container, but no Makefile, no production Dockerfile, no GitHub Actions workflows, and no defined contract for how local development, CI tests, AWS data lake access, and deployment relate to each other.

The developer also needs a phased approach that does not over-build infrastructure before the core investment pipeline exists (data ingestion → permanent loss filter → quality and cheapness scoring → ranking → model portfolio → backtest → sell-watch). Without an explicit CI/CD plan, work on the data lake and AWS risks becoming confusing: it is unclear what runs locally, what runs in CI, what touches S3, and when full continuous deployment should begin.

## Solution

Establish a **Phase 0 CI/CD foundation** that separates three concerns:

1. **Fast, deterministic PR CI** — lint and unit/smoke tests against pinned fixtures; no network, no AWS, no live SEC or price provider calls.
2. **Independent AWS integration tier** — a manual and scheduled workflow that proves ingestion can write to the dev S3 data lake using GitHub OIDC (no long-lived AWS keys).
3. **Deferred full CD (Phase 1–2)** — after the pipeline container and business logic exist, deploy to ECS Fargate on merge to `develop` (dev) and `main` (prod with approval), using multiple Docker images over time but shipping only the **pipeline image** first.

The data lake uses the **same layout everywhere** (raw, curated, point-in-time zones) with a configurable lake root URI: local file mirror for optional offline work, S3 dev bucket as the canonical store for real ingestion, S3 prod bucket for promoted runs. DuckDB reads Parquet from either backend.

GitFlow maps environments: pull requests run CI on all branches; merge to `develop` eventually deploys dev; merge to `main` eventually deploys prod behind a GitHub Environment approval gate.

## User Stories

1. As a developer, I want a single Makefile with standard targets for install, lint, test, and local ingestion, so that dev, CI, and documentation all reference the same commands.
2. As a developer, I want Poetry to manage Python 3.11 dependencies and an in-project virtualenv, so that the environment matches the devcontainer and CI runners.
3. As a developer, I want PR CI to run automatically on every pull request, so that broken changes are caught before merge.
4. As a developer, I want PR CI to complete quickly without external network calls, so that feedback is reliable and merges are not blocked by SEC or yfinance outages.
5. As a developer, I want unit and smoke tests to use pinned fixtures representing universe, fundamentals, and prices, so that scoring and filtering logic is testable without a live data lake.
6. As a developer, I want Ruff to enforce lint and format checks in CI, so that code quality is consistent from day one.
7. As a developer, I want a smoke test that exercises the core pipeline path on fixtures (permanent loss → ROC → EY → combined rank → portfolio selection), so that regressions in the vertical slice are caught early.
8. As a developer, I want real data ingestion to target AWS S3 in a dev bucket, so that the project demonstrates cloud-native data lake practice rather than local-only storage.
9. As a developer, I want ingestion tested independently from PR CI via a separate workflow, so that AWS integration is proven without making every PR flaky or slow.
10. As a developer, I want the ingest integration workflow to be triggerable manually and on a weekly schedule, so that I can validate connectors after changes without waiting for a release.
11. As a developer, I want separate dev and prod S3 buckets from the start, so that test artifacts never mix with production data and IAM can be scoped correctly.
12. As a developer, I want GitHub Actions to authenticate to AWS via OIDC role assumption, so that no long-lived AWS access keys are stored in GitHub Secrets.
13. As a developer, I want distinct IAM roles for dev and prod GitHub environments, so that production permissions are tighter and auditable.
14. As a developer, I want a pipeline Docker image that is separate from future dashboard and control-plane images, so that batch jobs stay minimal and deploy boundaries are clear.
15. As a developer, I want only the pipeline image built and deployed in Phase 0–1, so that infrastructure work stays proportional to existing application code.
16. As a developer, I want the pipeline container to run on ECS Fargate (Spot where viable), so that daily batch execution is cost-effective and aligned with the architecture doc.
17. As a developer, I want merge to `develop` to eventually deploy to the dev environment (ECR tag + ECS task revision), so that integrated changes are runnable in AWS before production.
18. As a developer, I want merge to `main` to eventually deploy to prod with a required GitHub Environment approval, so that production promotion is deliberate.
19. As a developer, I want runtime secrets (API keys, broker credentials) sourced from AWS Secrets Manager at task runtime, so that secrets never live in the repository or container image.
20. As a developer, I want build-time configuration limited to non-secret environment identifiers (bucket names, regions, cluster names), so that the security model matches architecture decisions.
21. As a developer, I want a configurable lake root URI so the same ingestion and query code works against local mirrors and S3, so that I understand the data lake as layout plus Parquet, not as “local vs cloud” code forks.
22. As a developer, I want an optional gitignored local lake mirror for speed or offline work, so that I am not blocked when AWS is unavailable, without making local storage the source of truth.
23. As a developer, I want the permanent loss filter regression cases (Enron, Lehman, WorldCom) to run in CI once that module exists, so that bankruptcy/fraud exclusions remain auditable.
24. As a developer, I want full 20-year walk-forward backtests to run outside PR CI (manual or scheduled), so that long-running validation does not block every commit.
25. As a developer, I want CI to respect point-in-time correctness in fixture design, so that tests reinforce the project’s core constraint against look-ahead bias.
26. As a portfolio reviewer, I want the README and docs to explain the three-tier testing model (fixtures / AWS ingest-smoke / deploy), so that the MLOps story is interview-ready.
27. As a developer, I want Prefect orchestration deferred until the ECS task path works, so that scheduling complexity does not block the first end-to-end AWS run.
28. As a developer, I want the Streamlit dashboard image and CD deferred until dashboard code exists, so that deploy pipelines are not empty scaffolding.
29. As a developer, I want MLflow experiment tracking integrated after the pipeline stabilizes, so that run snapshots do not slow initial delivery.
30. As a developer, I want infrastructure definitions (buckets, OIDC provider, IAM roles, ECR repository, ECS cluster skeleton) versioned alongside the application, so that AWS setup is reproducible.
31. As a developer, I want conventional commit and GitFlow branch conventions documented and followed, so that `develop` and `main` map cleanly to dev and prod deploy workflows.
32. As a developer, I want the devcontainer to remain development-only and not used as the CI runner image, so that dev ergonomics and production slim images stay separate concerns.
33. As a developer, I want ECR images tagged with git commit SHA and environment labels, so that any ECS run is traceable to source control.
34. As a developer, I want CloudWatch Logs as the initial observability sink for ECS tasks, so that pipeline failures are debuggable without heavier tooling.
35. As a developer, I want a clear milestone sequence from M0 (Makefile + CI) through M4 (Fargate runs pipeline in dev) before prod CD, so that implementation order is unambiguous.

## Implementation Decisions

### Scope and phasing

- **Phase 0 (now):** Makefile, Poetry groups, PR CI workflow, fixture layout, pipeline package skeleton, ingest-smoke workflow to dev S3, OIDC + bucket provisioning. No full deploy on every merge yet.
- **Phase 1:** Pipeline Dockerfile, ECR push on merge to `develop`, ECS Fargate task definition update for dev.
- **Phase 2:** Prod deploy on merge to `main` with GitHub Environment approval; prod OIDC role and prod bucket writes restricted to promoted tasks.
- **Phase 3+:** Prefect orchestration, dashboard image, MLflow server, EventBridge daily schedule — explicitly later.

### Deployable units (multi-image, pipeline first)

- Target architecture uses **multiple Docker images** over the MVP lifetime: pipeline worker (batch), dashboard (Streamlit), and optionally separate control-plane services.
- **Phase 0–1 ships only the pipeline image.** Dashboard and Prefect worker images are out of scope until their application modules exist.
- The pipeline image entrypoint runs batch stages (ingest, normalize, score, rank, backtest slice, sell-watch) driven by CLI subcommands or a single orchestrated command — exact CLI shape to be defined during M1 implementation.

### Data lake and environment configuration

- Lake layout follows architecture zones: **raw** (immutable provider payloads), **curated** (normalized Parquet), **pit** (point-in-time store keyed by as-of date), plus **curated/issues** for the review queue.
- A single configuration value, **lake root URI**, selects the storage backend:
  - Local optional mirror: file-backed root under a gitignored directory for developer convenience.
  - Dev canonical store: S3 dev bucket prefix.
  - Prod store: S3 prod bucket prefix.
- DuckDB is the analytical engine reading Parquet from the configured root; no Athena in MVP.
- **CI does not read or write live S3.** Integration workflows use dev bucket only.

### CI workflow (every pull request)

- Triggers on pull requests targeting `develop` or `main` (and optionally other long-lived branches if added).
- Steps: checkout → Python 3.11 + Poetry install → `make lint` → `make test` → `make test-smoke`.
- **Lint:** Ruff check and format check on application and test packages.
- **Unit tests:** pytest with markers excluding integration tests; all data from committed fixtures.
- **Smoke test:** end-to-end pipeline on a tiny fixture universe proving the vertical slice wiring (may initially stub modules until implemented).
- No AWS credentials configured on PR workflows.
- No live calls to SEC EDGAR, yfinance, or paid API tiers.

### AWS integration workflow (ingest-smoke)

- Separate workflow from PR CI; triggers: `workflow_dispatch` and weekly cron.
- Runs against **GitHub Environment `dev`** with OIDC assumption of the dev IAM role.
- Executes a minimal ingestion job (small ticker subset) writing to the dev bucket raw zone, then validates object presence and basic schema/count checks.
- Failures notify via workflow status; they do not block unrelated PR merges unless explicitly wired later.

### Authentication and IAM

- **GitHub OIDC → AWS IAM role assumption** is mandatory; static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in GitHub Secrets are out of scope.
- Two roles minimum: **dev GitHub Actions role** (dev bucket read/write, dev ECR push, dev ECS register task definition) and **prod GitHub Actions role** (prod bucket, prod ECR, prod ECS — tighter trust policy, main branch only).
- Runtime tasks use **task execution roles** distinct from GitHub deploy roles; secrets read from AWS Secrets Manager at container start.
- Trust policies restrict repository, environment, and branch refs.

### Storage and registry

- Two S3 buckets from day one: **dev** and **prod**, with consistent prefix conventions for lake zones, cache, and future MLflow artifacts.
- One ECR repository (or repository per image type later) for the pipeline image; tags include commit SHA and environment (`dev-<sha>`, `prod-<sha>`, optional `latest-dev` / `latest-prod`).

### Runtime and orchestration

- **ECS Fargate** is the first-class CD target for the pipeline container (Spot where appropriate for cost).
- AWS Batch is a future alternative if job queue semantics become necessary; not Phase 0.
- **Prefect** orchestration is deferred; initial runs may be one-off Fargate tasks triggered by deploy workflow or manual run-task until Prefect is introduced.

### Branching and deployment mapping (GitFlow)

- Feature branches → PR → CI only.
- Merge to **`develop`** → Phase 1+ deploy dev (build, push ECR, update ECS task).
- Merge to **`main`** → Phase 2 deploy prod with required reviewer on GitHub `production` environment.
- Hotfix flow may merge to `main` and back to `develop`; deploy workflows must respect branch protections.

### Application modules touched or introduced

Deep modules (simple interfaces, testable in isolation):

| Module | Responsibility | Phase |
| --- | --- | --- |
| **Configuration** | Lake root URI, environment name, AWS region, non-secret resource names | M0 |
| **Lake I/O** | Read/write Parquet under raw/curated/pit prefixes; abstract file vs S3 | M1 |
| **Ingestion connectors** | SEC EDGAR and price providers → raw zone | M1–M2 |
| **Normalization + PIT** | Curated schema, as-of date tagging, incremental refresh | M2 |
| **Permanent loss filter** | Hard exclusions for fraud/bankruptcy | M1 |
| **Scoring** | ROC rank, EY rank, combined rank | M1 |
| **Portfolio selection** | Top combined rank → 15–30 name model portfolio | M1 |
| **Backtest runner** | Walk-forward on PIT data; pass/fail vs benchmarks | M2+ |
| **Sell-watch** | Daily signals on model holdings | M2+ |
| **Pipeline CLI** | Subcommands invoked locally, in CI smoke, and in container | M1 |

Makefile targets wrap Poetry commands so CI and humans share entrypoints: install, lint, test, test-smoke, local ingest, docker build (pipeline), and later deploy helpers.

### Poetry dependency strategy

- Single Poetry project for the repository.
- **Dev group:** pytest, ruff; optional moto for S3 mock unit tests if needed.
- **Pipeline optional/extras group:** duckdb, boto3, pyarrow, sec-edgar-downloader, and other pipeline dependencies as modules land — avoid bloating dev-only installs.
- Enable package mode once the application package under `src/` exists.

### Relationship to devcontainer

- The existing devcontainer remains **development-only** (Docker-in-Docker, AWS CLI, Poetry, Jupyter, forwarded ports for future Streamlit/MLflow).
- CI uses GitHub-hosted runners with Makefile + Poetry; it does not build or run the devcontainer image.
- Production pipeline Dockerfile is slim and separate from the devcontainer Dockerfile.

### Milestone sequence

| Milestone | Deliverable |
| --- | --- |
| **M0** | Makefile, Poetry dev groups, PR CI workflow, empty package + passing smoke stub, fixture directory |
| **M1** | Core modules on fixtures; permanent loss + scoring + rank smoke green; package mode on |
| **M2** | Dev/prod buckets, OIDC roles, ingest-smoke workflow green against dev S3 |
| **M3** | Pipeline Dockerfile, ECR push on merge to `develop` |
| **M4** | ECS Fargate task runs pipeline in dev with `LAKE_URI` pointing at dev bucket |
| **M5** | Prod deploy on `main` with approval gate |
| **M6** | Prefect, dashboard image, MLflow, scheduled daily runs |

## Testing Decisions

### What makes a good test here

- Test **observable behavior** at module boundaries: given fixture inputs and a run date, expect exclusions, ranks, portfolio membership, or sell signals — not internal function call order.
- Fixture data must respect **point-in-time** semantics: each fundamental row carries an as-of date; tests pass only when queries filter `as_of_date <= run_date`.
- CI tests must be **hermetic**: no network, no AWS, deterministic ordering where ranks are involved.
- Integration tests that hit S3 or live APIs live in a **separate workflow or marker** (`integration`) and are never required for every PR.

### Modules to test in PR CI

| Module | Test type | Notes |
| --- | --- | --- |
| Configuration | Unit | Default lake URI, env overrides |
| Permanent loss filter | Unit + regression | Enron, Lehman, WorldCom must be hard-excluded at correct as-of dates when module exists |
| ROC / EY scoring | Unit | Known EBIT, capital, EV → expected ranks on tiny cross-section |
| Combined rank + portfolio | Smoke | Fixture universe → expected top-N names |
| Pipeline CLI smoke | Smoke | Invokes wired stages sequentially on fixtures |
| Lake I/O | Unit | Optional moto or local temp dirs; not live S3 in PR CI |

### Modules tested outside PR CI

| Module | Test type | Notes |
| --- | --- | --- |
| Ingestion connectors | Integration (ingest-smoke workflow) | Tiny live pull → dev S3 raw zone |
| Full backtest | Scheduled / manual | 20+ year walk-forward too slow for PR |
| ECS deploy | Post-deploy smoke | Run task after dev deploy; assert exit code and logs |

### Prior art

- Devcontainer PRD validated tooling via manual smoke checks (Python, Poetry, AWS CLI, Ruff, pytest).
- Architecture doc specifies Enron / Lehman / WorldCom regression in CI for the permanent loss filter — adopt when that module is implemented.
- Legacy notebooks and `src/` exploration are not test prior art; new tests live under the package test tree with fixtures.

## Out of Scope

- **Prefect** orchestration and Prefect Cloud/server setup in Phase 0–1.
- **Streamlit dashboard** Docker image and dashboard CD.
- **MLflow tracking server** on EC2 and artifact promotion workflows.
- **Full continuous deployment on day one** (Phase 0 is CI + ingest-smoke only).
- **Kubernetes / EKS** and AWS Batch as primary runtime (Batch remains a later option).
- **Static AWS access keys** in GitHub Secrets.
- **Single fat Docker image** for dashboard + pipeline + MLflow.
- **CI ingestion or scoring against live SEC/yfinance on every PR.**
- **Prod bucket writes** before Phase 2 prod deploy exists.
- **Transaction costs, taxes, live broker execution** — product scope, not CI/CD scope.
- **Terraform vs CDK choice** — infrastructure-as-code tool may be chosen during M2; not blocking M0.
- **Ruff/pytest detailed rule configuration** beyond enabling tools in Phase 0 (may follow as chore).

## Further Notes

- This PRD captures decisions from the CI/CD design session (grill-me). It should be reflected in a future feature spec under `docs/mvp/features/` (e.g. `cicd-infrastructure.md`) and cross-linked from `docs/mvp/architecture/architecture.md` when implementation starts — per spec-driven workflow, the feature spec becomes canonical for acceptance criteria and implementation status.
- The core product vertical slice remains: ingest → permanent loss filter → quality (ROC) → cheapness (EY) → combined rank → model portfolio (~30 names) → backtest → sell-watch. CI/CD serves that slice, not the reverse.
- Cost awareness: dev integration and ECS tasks should use minimal resource sizes and Spot where acceptable; align with the architecture soft budget (~low single-digit USD/month for control plane before storage growth).
- When implementation begins, update `docs/README.md` to index this PRD under an MVP PRDs section alongside the devcontainer PRD.
- GitHub issue creation with label `ready-for-agent` is recommended for tracking vertical implementation slices (`to-issues`), but this document is the saved PRD artifact at `docs/mvp/prds/ci-cd/ci-cd-prd.md` as requested.
