# Friday demo — local CSS path (operator)

10-minute local rehearsal: mart → fit (AUC/KS) → FastAPI `/score` + `/drivers` → serving Docker → **PSI**. No AWS required for the MUST path.

**Story:** public demo data → WOE+XGB `pipeline.joblib` (MLflow AUC/KS) → FastAPI score + risk drivers → same curls via serving Docker → local PSI report. Application credit risk ranking — not investing, not fraud, not a bureau score.

Glossary: [`../../CONTEXT.md`](../../CONTEXT.md) · Specs: [`../features/css-chapter5-mart-and-scoring.md`](../features/css-chapter5-mart-and-scoring.md), [`../features/psi-data-drift.md`](../features/psi-data-drift.md) · API detail: [`serve-fastapi.md`](serve-fastapi.md)

## 1. Fit → metrics → joblib

Hermetic fixture path (safe for git; do not commit `data/credit/` marts):

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/scoring_mart/applications.csv \
  --output-dir /tmp/credit_mart \
  --application-id-column customer_ID \
  --target-column target --bad-value 1 --good-value 0

export MLFLOW_TRACKING_URI="file://$(pwd)/mlruns"
export MLFLOW_ALLOW_FILE_STORE=true

poetry run credit-css fit \
  --mart /tmp/credit_mart/application_mart.parquet \
  --output-dir /tmp/credit_artifact \
  --application-id-column customer_ID \
  --target-column target
```

Call out from the CLI: holdout **AUC** / **KS**, MLflow run id, and `pipeline.joblib` under `/tmp/credit_artifact/`. (Optional: `mlflow ui --backend-store-uri "$MLFLOW_TRACKING_URI"` if you want the UI on screen. Use `--skip-mlflow` if you only need the joblib.)

For a PSI-stable develop/holdout story with 10 quantile bins, prefer the larger hermetic mart and keep the same paths for sections 4–5:

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/psi_mart/applications.csv \
  --output-dir /tmp/credit_mart_psi \
  --application-id-column customer_ID \
  --target-column target --bad-value 1 --good-value 0

poetry run credit-css fit \
  --mart /tmp/credit_mart_psi/application_mart.parquet \
  --output-dir /tmp/credit_artifact_psi \
  --application-id-column customer_ID \
  --target-column target
```

## 2. Serve → score → drivers

```bash
export CREDIT_PIPELINE_ARTIFACT=/tmp/credit_artifact/pipeline.joblib
# If you fitted the psi_mart path above, use:
# export CREDIT_PIPELINE_ARTIFACT=/tmp/credit_artifact_psi/pipeline.joblib
poetry run credit-css-serve
```

Example payloads (fixture-derived):

- `tests/credit/fixtures/serving/score_request.json`
- `tests/credit/fixtures/serving/drivers_request.json`

```bash
curl -s localhost:8000/health
curl -s localhost:8000/score \
  -H 'content-type: application/json' \
  -d @tests/credit/fixtures/serving/score_request.json
curl -s localhost:8000/drivers \
  -H 'content-type: application/json' \
  -d @tests/credit/fixtures/serving/drivers_request.json
```

Show: `pd`, `credit_score`, `rank` (rank-only, no cutoff); then top-k drivers by **gain × |WOE|** (not SHAP unless stretch landed).

## 3. Same path in serving Docker

```bash
docker build -f credit/Dockerfile.serve -t credit-css-serve .
docker run --rm -p 8000:8000 \
  -e CREDIT_PIPELINE_ARTIFACT=/artifact/pipeline.joblib \
  -v /tmp/credit_artifact:/artifact:ro \
  credit-css-serve
```

If you used the psi_mart fit, mount `/tmp/credit_artifact_psi` instead of `/tmp/credit_artifact`. Repeat the `/score` and `/drivers` curls against the container.

## 4. PSI — stable scenario (develop vs holdout)

Same mart split as fit (`--holdout-fraction` / `--random-state` defaults match fit):

```bash
poetry run credit-css psi \
  --mart /tmp/credit_mart_psi/application_mart.parquet \
  --artifact /tmp/credit_artifact_psi/pipeline.joblib \
  --output-dir /tmp/credit_psi_stable

cat /tmp/credit_psi_stable/psi_report.md
```

Monitors `credit_score`, `pd`, and top-IV features (up to 10). Thresholds default to stable &lt; 0.10, shift &lt; 0.25, severe ≥ 0.25.

## 5. PSI — synthetic drift (forced red)

```bash
poetry run credit-css psi \
  --mart /tmp/credit_mart_psi/application_mart.parquet \
  --artifact /tmp/credit_artifact_psi/pipeline.joblib \
  --output-dir /tmp/credit_psi_drift \
  --synthetic-drift

cat /tmp/credit_psi_drift/psi_report.md
```

Copies the recent (holdout) batch, shift/scales 1–2 top-IV features (fixed seed), rescores, then reports PSI. Shifted columns should land in **severe**.

## Honest limits (say out loud)

- Public demo data only — not live bank BFSI.
- Rank-only (no approve/decline cutoff).
- Drivers = gain × |WOE|; SHAP = stretch.
- PSI v1 = local Markdown + JSON file report — not an interactive drift dashboard.
- AWS public URL / Terraform up-down = stretch, not MUST — see [`../features/aws-fargate-serve-demo.md`](../features/aws-fargate-serve-demo.md) (ADR-0004).
