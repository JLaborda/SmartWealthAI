# Credit — CSS (Credit Scoring System)

**Domain:** application credit scoring (default risk ranking at origination).

**Status:** book path done; competition raw (#151) + competition mart (#152) done; AMEX categoricals fixed ([#157](https://github.com/JLaborda/SmartWealthAI/issues/157)); **scratch scoring + thin MLOps (#145)** — `fit` → `pipeline.joblib` → `score` / Docker batch; FastAPI serving later. Competition EDA ([#153](https://github.com/JLaborda/SmartWealthAI/issues/153)) remains parallel. Elliot Taehun Kim (2026), *Financial AI in Practice*, chapters 5–6, local-first. Glossary: [`CONTEXT.md`](CONTEXT.md) · Portfolio map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) · Specs: [`docs/`](docs/)

## What it will do

Build an **application mart** from public demo data → WOE/IV → model → probability → **credit score** → rank applications by risk (AUC + KS on holdout). Chapter 6 adds OptBinning scorecard, drift monitoring, and explainability.

This is **not** fraud detection and **not** the investing screener.

## Data (demo only)

No live bank BFSI data. Book sample (AMEX-shaped) is in Git LFS at [`credit/data/train_df_sample.pkl`](data/train_df_sample.pkl) — see [`credit/data/README.md`](data/README.md) for schema, **target** → **bad**/**good**, and `git lfs pull`. **Priority:** official Kaggle **raw competition extracts** (AMEX + Home Credit) under gitignored `data/credit/raw/` (#151) — not committed; access-only (no submissions). FICO HELOC documented for later. Hermetic CI uses `tests/credit/fixtures/`. Always document the **target** → **bad**/**good** mapping on the mart README sidecar.

### Local mart + EDA (book sample)

```bash
git lfs pull --include="credit/data/*"
poetry run credit-css build-application-mart \
  --source credit/data/train_df_sample.pkl \
  --output-dir data/credit/application_mart \
  --application-id-column customer_ID \
  --target-column target \
  --bad-value 1 \
  --good-value 0
# Exploration notebook (optional; not CI):
# credit/notebooks/eda_application_mart.ipynb
```

### Competition marts (AMEX / Home Credit)

After staging raw extracts (see [`credit/data/README.md`](data/README.md)):

```bash
poetry run credit-css build-competition-mart \
  --source-kind amex \
  --raw-dir data/credit/raw/amex \
  --output-dir data/credit/application_mart/amex
poetry run credit-css build-competition-mart \
  --source-kind home_credit \
  --raw-dir data/credit/raw/home_credit \
  --output-dir data/credit/application_mart/home_credit
```

**AMEX prepare contract** (statement → one row per `customer_ID`, ordered by `S_2`):

- Continuous numerics → `{col}_mean` / `_std` / `_min` / `_max` / `_last`
- Official categoricals (`B_30`, `B_38`, `D_114`, `D_116`, `D_117`, `D_120`, `D_126`, `D_63`, `D_64`, `D_66`, `D_68`) and any other non-numeric statement features → `{col}_mode` / `{col}_last` only (e.g. `D_63_mode`, `D_63_last`)
- Labels: inner join `train_labels.csv`; `target` **1 = bad**, **0 = good**
- Dating: **static competition data** — not point-in-time / as-of dated; develop/holdout is stratified random only
- Runtime: full official `train_data.parquet` (~4 GB / 5.5M statement rows) is minutes, not seconds — expect ~3–5 min wall time on a laptop after load; hermetic CI fixtures stay tiny.

Mart parquet under `data/credit/` is gitignored. Fixture CSV path remains the hermetic CI default:

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/application_source/applications.csv \
  --output-dir data/credit/application_mart
```

### Scratch scoring (#145) — fit → joblib → score

Hermetic fixture (CI):

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/scoring_mart/applications.csv \
  --output-dir /tmp/credit_mart \
  --application-id-column customer_ID \
  --target-column target \
  --bad-value 1 \
  --good-value 0

export MLFLOW_TRACKING_URI="file://$(pwd)/mlruns"
export MLFLOW_ALLOW_FILE_STORE=true
poetry run credit-css fit \
  --mart /tmp/credit_mart/application_mart.parquet \
  --output-dir /tmp/credit_artifact \
  --application-id-column customer_ID \
  --target-column target

poetry run credit-css score \
  --artifact /tmp/credit_artifact/pipeline.joblib \
  --mart /tmp/credit_mart/application_mart.parquet \
  --output /tmp/credit_scores.parquet
```

**EDA wrap defaults (locked):** 80% null drop; prefer `B_38_last`; WOE both `P_2_last` and `D_48_last` then drop the weaker by develop IV; no `B_38×B_30` interaction.

**Artifact:** `pipeline.joblib` holds WOE/IV binner + XGBoost + score-scaling params. Rank-only (no cutoff). Holdout AUC + KS printed on `fit`.

**Score scaling:** interim textbook defaults (PDO=20, base_score=600, base_odds=50) until book notebook params are confirmed.

### Docker batch score

Build from repo root (same artifact the CLI writes):

```bash
docker build -f credit/Dockerfile -t credit-css-score .
docker run --rm \
  -v /tmp/credit_artifact:/artifact:ro \
  -v /tmp/credit_mart:/mart:ro \
  -v /tmp/credit_out:/out \
  credit-css-score \
  --artifact /artifact/pipeline.joblib \
  --mart /mart/application_mart.parquet \
  --output /out/scores.parquet
```

FastAPI serving of the same `pipeline.joblib` is a **later PR** (not this image).


## Delivery cuts

| Cut | Scope |
| --- | --- |
| **PR1** | Application mart (load / clean / validate) + CLI |
| **EDA** | Notebook on mart output (balance, missingness, exploratory views) — [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) |
| **PR2 / #145** | WOE/IV + XGBoost + book probability→score scaling + rank-only CLI (AUC + KS) + `pipeline.joblib` + MLflow + Docker batch score |
| Later | FastAPI serving of the same joblib |
| Later | Chapter 6 scorecard / monitoring / explainability |
| Later | Approve/decline cutoff (profit/risk); `platform/` (AWS / Terraform) |

## Packaging

One Poetry project at repo root: `credit` is a second installable package
(`credit/src/credit`) beside investing — `poetry install` is enough.

CLI (package scaffold [#143](https://github.com/JLaborda/SmartWealthAI/issues/143); mart stage [#144](https://github.com/JLaborda/SmartWealthAI/issues/144)):

```bash
poetry run credit-css --help
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/application_source/applications.csv \
  --output-dir data/credit/application_mart
poetry run credit-css fit --help
poetry run credit-css score --help
poetry run python -m credit build-application-mart --help
```

Hermetic CI uses fixtures under `tests/credit/fixtures/` (including `scoring_mart/` for #145). The mart README sidecar documents **target** → **bad**/**good** and the develop/holdout policy.

Feature spec: [`docs/features/css-chapter5-mart-and-scoring.md`](docs/features/css-chapter5-mart-and-scoring.md)
(parent [#142](https://github.com/JLaborda/SmartWealthAI/issues/142)).
Orchestration is **CLI + stages** (not Airflow locally).

## Sources

1. **Elliot Taehun Kim (2026)** — *Financial AI in Practice: A Playbook for Credit, Fraud, and Investment Systems*
   Architecture patterns, feature engineering, and ML pipelines for credit risk (CSS follows chapters 5–6).

Full portfolio Sources: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md).
