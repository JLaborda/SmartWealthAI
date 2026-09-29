# Credit — CSS (Credit Scoring System)

**Domain:** application credit scoring (default risk ranking at origination).

**Status:** planned — Elliot Taehun Kim (2026), *Financial AI in Practice*, chapters 5–6, local-first. Glossary: [`CONTEXT.md`](CONTEXT.md) · Portfolio map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) · Specs: [`docs/`](docs/)

## What it will do

Build an **application mart** from public demo data → WOE/IV → model → probability → **credit score** → rank applications by risk (AUC + KS on holdout). Chapter 6 adds OptBinning scorecard, drift monitoring, and explainability.

This is **not** fraud detection and **not** the investing screener.

## Data (demo only)

No live bank BFSI data. Prefer the book sample after Git LFS; practical fallbacks: **Home Credit**, then **FICO HELOC**. AMEX Default Prediction is optional/scale-only (too large for v1). Always document the **target** → **bad**/**good** mapping on the mart README.

## Delivery cuts

| Cut | Scope |
| --- | --- |
| **PR1** | Application mart (load / clean / validate) + CLI |
| **EDA** | Notebook on mart output (balance, missingness, exploratory views) — [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) |
| **PR2** | WOE/IV + XGBoost + book probability→score scaling + rank-only CLI (AUC + KS) |
| Later | Chapter 6 scorecard / monitoring / explainability |
| Later | Approve/decline cutoff (profit/risk); `platform/` (AWS / Terraform) |

## Packaging

One Poetry project at repo root: `credit` is a second installable package beside investing — `poetry install` is enough. Orchestration is **CLI + stages** (not Airflow locally).

## Sources

1. **Elliot Taehun Kim (2026)** — *Financial AI in Practice: A Playbook for Credit, Fraud, and Investment Systems*
   Architecture patterns, feature engineering, and ML pipelines for credit risk (CSS follows chapters 5–6).

Full portfolio Sources: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md).
