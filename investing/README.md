# Investing

**Domain:** quantitative value / Magic Formula screening on US equities.

**Status:** June 30 demo slice **delivered** (v0.1.0). Code still lives under `src/smartwealthai/`, `apps/dashboard/`, and `docs/mvp/` until a dedicated migrate-only PR moves it here (portfolio layout B+).

## What it does

Ingest SimFin fundamentals → point-in-time curated lake → universe (US minus banks/insurers/utilities) → ROC + Earnings Yield ranks → combined rank → top-30 equal-weight **model portfolio** → Streamlit dashboard + MLflow run logging.

## How to run (today)

From the repo root (Poetry):

```bash
export SIMFIN_API_KEY="<from user secrets>"
poetry run run-demo-pipeline --run-date 2026-06-18
poetry run run-dashboard --data-dir data --run-date 2026-06-18
```

Docs: [`docs/mvp/demo-slice.md`](../docs/mvp/demo-slice.md) · Glossary: [`CONTEXT.md`](../CONTEXT.md) · Map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md)

## Not in active roadmap

Phase 2 Quantitative Value (forensics, FS-Score, full backtest, sell-watch as production path) is **cancelled for execution**. Cloud patterns may return later under `platform/`, shared with other domains.
