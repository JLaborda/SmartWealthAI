# 📈 SmartWealthAI

[![Tests](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml/badge.svg)](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/JLaborda/SmartWealthAI?branch=main&label=coverage)](https://codecov.io/gh/JLaborda/SmartWealthAI)

**Portfolio monorepo for finance engineering:** distinct domains a manager can spot at a glance.

| Domain | Path | Status |
| --- | --- | --- |
| **Investing** (Magic Formula / value screening) | [`investing/`](investing/) | Demo slice **v0.1.0** delivered |
| **Credit** — CSS (Credit Scoring System) | [`credit/`](credit/) | Planned (book ch.5–6, local-first) |
| **Fraud** | `fraud/` | Not started |
| **Platform** (AWS / Terraform) | `platform/` | After domain demos work locally |

Map & relationships: [`CONTEXT-MAP.md`](CONTEXT-MAP.md) · Investing glossary: [`CONTEXT.md`](CONTEXT.md) · Credit glossary: [`credit/CONTEXT.md`](credit/CONTEXT.md)

---

## Investing (shipped)

Greenblatt-style ranking on US equities: SimFin → PIT lake → ROC + EY → top-30 EW model portfolio → Streamlit + MLflow.

*Code today:* `src/smartwealthai/` + `apps/dashboard/` + [`docs/mvp/`](docs/mvp/) (migration into `investing/` is a later housekeeping PR).

### Quickstart (investing demo)

```bash
poetry install
export SIMFIN_API_KEY="<from user secrets>"
poetry run run-demo-pipeline --run-date 2026-06-18
poetry run run-dashboard --data-dir data --run-date 2026-06-18
```

See [`investing/README.md`](investing/) and [`docs/mvp/demo-slice.md`](docs/mvp/demo-slice.md).

### Tech stack (investing)

* **Language:** Python 3.11+ · **Deps:** Poetry (uv migration later, after credit demo works)
* **Data:** SimFin bulk · **Libs:** pandas, simfin, yfinance, streamlit, mlflow-skinny

---

## Credit (next)

Application **CSS**: public demo data → application mart → scoring → rank by default risk. Specs and code land under [`credit/`](credit/).

---

## Roadmap (portfolio)

1. **Credit PR1–PR2** — mart, then chapter 5 scratch model + score (local CLI).
2. **Credit chapter 6** — OptBinning scorecard, monitoring, explainability.
3. **`platform/`** — Terraform / AWS; orchestrator choice open (Airflow vs EventBridge/ECS vs Prefect).
4. Optional: migrate investing code into `investing/`; Poetry → uv; fraud module.

Phase 2 Quantitative Value (as production investing path) is **not** in active execution.
