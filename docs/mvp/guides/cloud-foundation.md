# Cloud foundation (Phase 2a)

Operator guide for **lake root URI**, the pipeline Docker image, and the **ingest-smoke** GitHub Actions workflow. Implements GitHub issue [#94](https://github.com/JLaborda/SmartWealthAI/issues/94). ECS Fargate deploy is [#95](https://github.com/JLaborda/SmartWealthAI/issues/95).

## Lake root URI

All ingest and scoring CLIs resolve storage from a single **lake root**:

| Source | Precedence |
| --- | --- |
| `--lake-root-uri` | 1 (highest) |
| `--data-dir` | 2 |
| `LAKE_ROOT_URI` env var | 3 |
| `SMARTWEALTHAI_DATA_DIR` env var | 4 |
| default `data/` | 5 |

Supported URI forms:

- `file:///absolute/path` or bare local path (`data`, `/tmp/lake`)
- `s3://bucket/prefix/` (parsed for cloud workflows; parquet I/O in this slice is **file-backend only**)

Example (local mirror):

```bash
export LAKE_ROOT_URI="file://$(pwd)/data"
poetry run score-universe --run-date 2026-06-18
```

Backward compatible:

```bash
poetry run score-universe --data-dir data --run-date 2026-06-18
```

## Pipeline Docker image

Build and smoke-test locally (no AWS):

```bash
make docker-build
docker run --rm smartwealthai-pipeline --help
docker run --rm \
  -e LAKE_ROOT_URI=file:///lake \
  -v "$(pwd)/tests/fixtures/lake:/lake:ro" \
  smartwealthai-pipeline \
  --run-date 2026-06-18 --portfolio-size 3 --quiet
```

The image entrypoint is `score-universe`. Override the command for other CLIs by installing Poetry in a dev image or extending the Dockerfile entrypoint in [#95](https://github.com/JLaborda/SmartWealthAI/issues/95).

## Ingest-smoke workflow

Workflow: [`.github/workflows/ingest-smoke.yml`](../../.github/workflows/ingest-smoke.yml)

- Triggers: manual `workflow_dispatch` and weekly cron (Mondays 06:00 UTC)
- Uses GitHub Environment **`dev`** and **OIDC** (no long-lived AWS access keys)
- Writes `raw/_smoke/ingest-smoke.txt` to the dev bucket and validates with `head-object`

### Human prerequisites (one-time AWS setup)

If buckets and OIDC are not yet provisioned in your AWS account:

1. **S3 dev bucket** — e.g. `smartwealthai-dev-lake` with optional prefix `data/`. Same zone layout as local: `raw/`, `curated/`, `curated/issues/`.
2. **GitHub OIDC provider** in IAM (issuer `token.actions.githubusercontent.com`, audience `sts.amazonaws.com`).
3. **IAM role** trusted by the repo and `environment:dev`, with `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on the dev bucket prefix.
4. **GitHub Environment `dev`** repository variables:

   | Variable | Example |
   | --- | --- |
   | `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-actions-dev` |
   | `AWS_REGION` | `us-east-1` |
   | `DEV_LAKE_BUCKET` | `smartwealthai-dev-lake` |
   | `DEV_LAKE_PREFIX` | `data/` (or empty string) |

5. **Runtime secrets (ECS, #95)** — `SIMFIN_API_KEY` in AWS Secrets Manager; not required for ingest-smoke marker upload.

Terraform or CloudFormation for the above is out of scope for #94; document and provision manually or in a future infra issue.

### Run ingest-smoke manually

GitHub → Actions → **Ingest smoke (dev S3)** → Run workflow (environment: `dev`).

## Three-tier testing model

| Tier | What runs | AWS / network |
| --- | --- | --- |
| **PR CI** | `make lint`, `pytest` on fixtures | None |
| **Ingest-smoke** | OIDC S3 marker + lake URI parse | Dev bucket only |
| **Deploy (#95)** | ECR push, ECS Fargate pipeline | Dev/prod on merge |

PR CI must stay hermetic: no SimFin, yfinance, or live S3.

## Phase 2a scope

- **Pipeline on AWS** (batch ingest + score) — this guide + Docker image + ingest-smoke
- **Dashboard local** — `poetry run run-dashboard` reads `SMARTWEALTHAI_DATA_DIR` or local `data/`
- Full scheduled ECS deploy, MLflow on S3, and Secrets Manager task injection: [#95](https://github.com/JLaborda/SmartWealthAI/issues/95)
