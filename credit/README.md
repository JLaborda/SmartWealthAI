# Credit — CSS (Credit Scoring System)

**Domain:** application credit scoring (default risk ranking at origination).

**Status:** application mart + book-sample EDA ([#147](https://github.com/JLaborda/SmartWealthAI/issues/147)); next: scratch scoring ([#145](https://github.com/JLaborda/SmartWealthAI/issues/145)). Elliot Taehun Kim (2026), *Financial AI in Practice*, chapters 5–6, local-first. Glossary: [`CONTEXT.md`](CONTEXT.md) · Portfolio map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) · Specs: [`docs/`](docs/)

## What it will do

Build an **application mart** from public demo data → WOE/IV → model → probability → **credit score** → rank applications by risk (AUC + KS on holdout). Chapter 6 adds OptBinning scorecard, drift monitoring, and explainability.

This is **not** fraud detection and **not** the investing screener.

## Data (demo only)

No live bank BFSI data. Book sample (AMEX-shaped) is in Git LFS at [`credit/data/train_df_sample.pkl`](data/train_df_sample.pkl) — see [`credit/data/README.md`](data/README.md) for schema, **target** → **bad**/**good**, and `git lfs pull`. Full Kaggle AMEX and Home Credit dumps come later and must not be committed. Hermetic CI uses `tests/credit/fixtures/`. Always document the **target** → **bad**/**good** mapping on the mart README sidecar.

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

Mart parquet under `data/credit/` is gitignored. Fixture CSV path remains the hermetic CI default:

```bash
poetry run credit-css build-application-mart \
  --source tests/credit/fixtures/application_source/applications.csv \
  --output-dir data/credit/application_mart
```


## Delivery cuts

| Cut | Scope |
| --- | --- |
| **PR1** | Application mart (load / clean / validate) + CLI |
| **EDA** | Notebook on mart output (balance, missingness, exploratory views) — [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) |
| **PR2** | WOE/IV + XGBoost + book probability→score scaling + rank-only CLI (AUC + KS) |
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
poetry run python -m credit build-application-mart --help
```

Hermetic CI uses the fixture under `tests/credit/fixtures/application_source/`. The mart README sidecar documents **target** → **bad**/**good** and the develop/holdout policy (documented only in PR1 — no partition files yet).

Feature spec: [`docs/features/css-chapter5-mart-and-scoring.md`](docs/features/css-chapter5-mart-and-scoring.md)
(parent [#142](https://github.com/JLaborda/SmartWealthAI/issues/142)).
Orchestration is **CLI + stages** (not Airflow locally).

## Sources

1. **Elliot Taehun Kim (2026)** — *Financial AI in Practice: A Playbook for Credit, Fraud, and Investment Systems*
   Architecture patterns, feature engineering, and ML pipelines for credit risk (CSS follows chapters 5–6).

Full portfolio Sources: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md).
