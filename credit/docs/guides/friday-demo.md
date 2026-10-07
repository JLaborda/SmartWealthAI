# Friday demo — local CSS path (operator)

10-minute local demo: mart → fit → score/API → **PSI**. No AWS required for the MUST path.

Glossary: [`../../CONTEXT.md`](../../CONTEXT.md) · Specs: [`../features/css-chapter5-mart-and-scoring.md`](../features/css-chapter5-mart-and-scoring.md), [`../features/psi-data-drift.md`](../features/psi-data-drift.md)

## 1. Fit (hermetic fixture)

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/scoring_mart/applications.csv \
  --output-dir /tmp/credit_mart \
  --application-id-column customer_ID \
  --target-column target --bad-value 1 --good-value 0

poetry run credit-css fit \
  --mart /tmp/credit_mart/application_mart.parquet \
  --output-dir /tmp/credit_artifact \
  --application-id-column customer_ID \
  --target-column target \
  --skip-mlflow
```

For a PSI-stable develop/holdout story with 10 quantile bins, prefer the larger hermetic mart:

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
  --target-column target \
  --skip-mlflow
```

## 2. FastAPI (optional in the same rehearsal)

See [`serve-fastapi.md`](serve-fastapi.md). Set `CREDIT_PIPELINE_ARTIFACT` to the `pipeline.joblib` from fit.

## 3. PSI — stable scenario (develop vs holdout)

Same mart split as fit (`--holdout-fraction` / `--random-state` defaults match fit):

```bash
poetry run credit-css psi \
  --mart /tmp/credit_mart_psi/application_mart.parquet \
  --artifact /tmp/credit_artifact_psi/pipeline.joblib \
  --output-dir /tmp/credit_psi_stable

# Inspect
cat /tmp/credit_psi_stable/psi_report.md
```

Monitors `credit_score`, `pd`, and top-IV features (up to 10). Thresholds default to stable &lt; 0.10, shift &lt; 0.25, severe ≥ 0.25.

## 4. PSI — synthetic drift (forced red)

```bash
poetry run credit-css psi \
  --mart /tmp/credit_mart_psi/application_mart.parquet \
  --artifact /tmp/credit_artifact_psi/pipeline.joblib \
  --output-dir /tmp/credit_psi_drift \
  --synthetic-drift

cat /tmp/credit_psi_drift/psi_report.md
```

Copies the recent (holdout) batch, shift/scales 1–2 top-IV features (fixed seed), rescores, then reports PSI. Shifted columns should land in **severe**.

## Honest limits

- Rank-only (no approve/decline cutoff).
- PSI v1 = local Markdown + JSON file report — not an interactive drift dashboard.
- SHAP and Terraform/`apply` are stretch, not MUST.
