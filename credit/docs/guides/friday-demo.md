# Friday demo stub (10 min) — CSS local path

Rehearsal script for the **June/Oct credit MVP** local green demo. Spec: [`../features/css-chapter5-mart-and-scoring.md`](../features/css-chapter5-mart-and-scoring.md). Operator detail for the API: [`serve-fastapi.md`](serve-fastapi.md).

**Story:** public demo data → WOE+XGB `pipeline.joblib` (MLflow AUC/KS) → FastAPI score + risk drivers → same curls via serving Docker. Application credit risk ranking — not investing, not fraud, not a bureau score.

## 1) Fit → MLflow metrics → joblib

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
  --application-id-column customer_ID --target-column target
```

Call out from the CLI: holdout **AUC** / **KS**, MLflow run id, and `pipeline.joblib` under `/tmp/credit_artifact/`. (Optional: `mlflow ui --backend-store-uri "$MLFLOW_TRACKING_URI"` if you want the UI on screen.)

## 2) Serve → score → drivers

```bash
export CREDIT_PIPELINE_ARTIFACT=/tmp/credit_artifact/pipeline.joblib
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

## 3) Same path in serving Docker

```bash
docker build -f credit/Dockerfile.serve -t credit-css-serve .
docker run --rm -p 8000:8000 \
  -e CREDIT_PIPELINE_ARTIFACT=/artifact/pipeline.joblib \
  -v /tmp/credit_artifact:/artifact:ro \
  credit-css-serve
```

Repeat the two curls against the container.

## 4) PSI (Wed+)

Local PSI reference-vs-recent batch is a **Friday MUST** but not in this stub yet — land the CLI mid-week, then paste the one-liner + threshold note here before rehearsal.

## Honest limits (say out loud)

- Public demo data only — not live bank BFSI.
- Drivers = gain × |WOE|; SHAP = stretch.
- No approve/decline cutoff; rank only.
- AWS public URL / Terraform apply = stretch (S3-first if anything ships).
