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

### Operator notes

```bash
make test
# or: poetry run pytest
```

- **Active fundamentals path:** [`docs/mvp/guides/download-simfin.md`](../docs/mvp/guides/download-simfin.md)
- **Frozen SEC spike:** [`docs/mvp/guides/download-fundamentals.md`](../docs/mvp/guides/download-fundamentals.md)
- More: [`AGENTS.md`](../AGENTS.md)

Docs: [`docs/mvp/demo-slice.md`](../docs/mvp/demo-slice.md) · Glossary: [`CONTEXT.md`](../CONTEXT.md) · Map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md)

## Not in active roadmap

Phase 2 Quantitative Value (forensics, FS-Score, full backtest, sell-watch as production path) is **cancelled for execution** ([ADR-0003](../docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`). Cloud patterns may return later under `platform/`, shared with other domains.

## Sources

1. **Joel Greenblatt (2010)** — *The Little Book That Still Beats the Market*
   Foundations of the Magic Formula: systematic ranking by return on capital (ROC) and earnings yield.

2. **Wesley R. Gray & Tobias E. Carlisle (2012)** — *Quantitative Value: A Practitioner's Guide to Automating Intelligent Investment and Eliminating Behavioral Errors*
   QV framework provenance only — **not in active execution** ([ADR-0003](../docs/adr/0003-phase2-qv-cancelled.md)).

Full portfolio Sources: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md).
