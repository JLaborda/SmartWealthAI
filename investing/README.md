# Investing

**Domain:** quantitative value / Magic Formula screening on US equities.

**Status:** June 30 demo slice **delivered** (v0.1.0). Layout mirrors `credit/`: package `investing`, specs under `docs/`, dashboard under `apps/dashboard/`, tests under `tests/`.

## What it does

Ingest SimFin fundamentals → point-in-time curated lake → universe (US minus banks/insurers/utilities) → ROC + Earnings Yield ranks → combined rank → top-30 equal-weight **model portfolio** → Streamlit dashboard + MLflow run logging.

## How to run

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

- **Active fundamentals path:** [`docs/guides/download-simfin.md`](docs/guides/download-simfin.md)
- **Frozen SEC spike:** [`docs/guides/download-fundamentals.md`](docs/guides/download-fundamentals.md)
- More: [`AGENTS.md`](../AGENTS.md)

Docs: [`docs/demo-slice.md`](docs/demo-slice.md) · Glossary: [`CONTEXT.md`](CONTEXT.md) · Map: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md)

## Layout

```text
investing/
  CONTEXT.md              # ubiquitous language
  docs/                   # demo slice, architecture, features, guides
  src/investing/          # Python package (formerly smartwealthai)
  apps/dashboard/         # Streamlit demo UI
  tests/                  # hermetic investing tests + lake fixtures
```

## Not in active roadmap

Phase 2 Quantitative Value (forensics, FS-Score, full backtest, sell-watch as production path) is **cancelled for execution** ([ADR-0003](../docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`). Cloud patterns may return later under `platform/`, shared with other domains.

## Sources

1. **Joel Greenblatt (2010)** — *The Little Book That Still Beats the Market*
2. **Wesley R. Gray & Tobias E. Carlisle (2012)** — *Quantitative Value* (provenance for cancelled Phase 2 QV)
