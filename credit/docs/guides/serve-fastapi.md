# Guide: serve CSS scores with FastAPI

Loads the same `pipeline.joblib` produced by `credit-css fit` (WOE/IV binner + XGBoost + score scaling). Spec: [`../features/css-chapter5-mart-and-scoring.md`](../features/css-chapter5-mart-and-scoring.md).

## Prerequisites

- `poetry install` at repo root
- A fitted artifact from `credit-css fit` (file named `pipeline.joblib`)

## Fit → serve

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/scoring_mart/applications.csv \
  --output-dir /tmp/credit_mart \
  --application-id-column customer_ID \
  --target-column target --bad-value 1 --good-value 0

poetry run credit-css fit \
  --mart /tmp/credit_mart/application_mart.parquet \
  --output-dir /tmp/credit_artifact \
  --application-id-column customer_ID --target-column target \
  --skip-mlflow

export CREDIT_PIPELINE_ARTIFACT=/tmp/credit_artifact/pipeline.joblib
poetry run credit-css-serve
```

Equivalent uvicorn:

```bash
export CREDIT_PIPELINE_ARTIFACT=/tmp/credit_artifact/pipeline.joblib
poetry run uvicorn credit.api:create_app --factory --host 0.0.0.0 --port 8000
```

If `CREDIT_PIPELINE_ARTIFACT` is unset or the file is missing, `credit-css-serve` exits with a clear error (exit code 2) and does not start uvicorn.

## Endpoints

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/health` | — | `status`, `artifact` path |
| POST | `/score` | `application_id` + `features` | `pd`, `credit_score`, `rank` |
| POST | `/drivers` | same + optional `top_k` | top-k drivers (`gain_x_abs_woe`) |

Example payloads (fixture-derived, safe for git):

- `tests/credit/fixtures/serving/score_request.json`
- `tests/credit/fixtures/serving/drivers_request.json`

```bash
curl -s localhost:8000/score \
  -H 'content-type: application/json' \
  -d @tests/credit/fixtures/serving/score_request.json

curl -s localhost:8000/drivers \
  -H 'content-type: application/json' \
  -d @tests/credit/fixtures/serving/drivers_request.json
```

## Docker (volume mount)

```bash
docker build -f credit/Dockerfile.serve -t credit-css-serve .
docker run --rm -p 8000:8000 \
  -e CREDIT_PIPELINE_ARTIFACT=/artifact/pipeline.joblib \
  -v /tmp/credit_artifact:/artifact:ro \
  credit-css-serve
```

## Docker (bake-image demo — no volume)

Hermetic fit into gitignored `credit/demo_artifact/`, then an image that embeds `pipeline.joblib` (for local smoke and later Fargate). Spec: [`../features/aws-fargate-serve-demo.md`](../features/aws-fargate-serve-demo.md) (#173).

```bash
./platform/scripts/prepare-serve-demo-artifact.sh
docker build -f credit/Dockerfile.serve.demo -t credit-css-serve-demo .
docker run --rm -p 8000:8000 credit-css-serve-demo
```

Same curls as above (no `-v`). Volume-mount `Dockerfile.serve` remains the default local path.

## Out of this guide

PSI CLI, Terraform/AWS up-down (#174), SHAP on drivers — later slices.
