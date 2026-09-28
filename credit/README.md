# Credit — CSS (Credit Scoring System)

**Domain:** application credit scoring (default risk ranking at origination).

**Status:** planned — chapter 5–6 of *Financial AI in Practice*, local-first. Glossary: [`CONTEXT.md`](CONTEXT.md) · Portfolio map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md)

## What it will do

Build an **application mart** from public demo data → WOE/IV → model → probability → **credit score** → rank applications by risk (AUC + KS on holdout). Chapter 6 adds OptBinning scorecard, drift monitoring, and explainability.

This is **not** fraud detection and **not** the investing screener.

## Data (demo only)

No live bank BFSI data. Prefer the book sample after Git LFS; practical fallbacks: **Home Credit**, then **FICO HELOC**. AMEX Default Prediction is optional/scale-only (too large for v1). Always document the **target** → **bad**/**good** mapping on the mart README.

## Delivery cuts

| Cut | Scope |
| --- | --- |
| **PR1** | Application mart (load / clean / validate) + CLI |
| **PR2** | WOE/IV + XGBoost + book probability→score scaling + rank-only CLI (AUC + KS) |
| Later | Chapter 6 scorecard / monitoring / explainability |
| Later | Approve/decline cutoff (profit/risk); `platform/` (AWS / Terraform) |

## Packaging

One Poetry project at repo root: `credit` is a second installable package beside investing — `poetry install` is enough. Orchestration is **CLI + stages** (not Airflow locally).
