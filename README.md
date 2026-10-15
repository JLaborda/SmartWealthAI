# 📈 SmartWealthAI

[![Tests](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml/badge.svg)](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/JLaborda/SmartWealthAI?branch=main&label=coverage)](https://codecov.io/gh/JLaborda/SmartWealthAI)

**Portfolio monorepo for finance engineering:** distinct domains a manager can spot at a glance.

| Domain | Path | Status |
| --- | --- | --- |
| **Investing** (Magic Formula / value screening) | [`investing/`](investing/) | Demo slice **v0.1.0** delivered |
| **Credit** — CSS (Credit Scoring System) | [`credit/`](credit/) | **Active** — mart + competition EDA landed; scratch scoring next ([#145](https://github.com/JLaborda/SmartWealthAI/issues/145)) |
| **Fraud** | `fraud/` | Not started |
| **Platform** (AWS / Terraform) | `platform/` | After domain demos work locally |

Map & relationships: [`CONTEXT-MAP.md`](CONTEXT-MAP.md) · Investing glossary: [`investing/CONTEXT.md`](investing/CONTEXT.md) · Credit glossary: [`credit/CONTEXT.md`](credit/CONTEXT.md)

---

## Investing (shipped)

Greenblatt-style ranking on US equities: SimFin → PIT lake → ROC + EY → top-30 EW model portfolio → Streamlit + MLflow.

*Code:* [`investing/src/investing/`](investing/src/investing/) · Dashboard: [`investing/apps/dashboard/`](investing/apps/dashboard/) · Specs: [`investing/docs/`](investing/docs/)

### Quickstart (investing demo)

```bash
uv sync
export SIMFIN_API_KEY="<from user secrets>"
uv run run-demo-pipeline --run-date 2026-06-18
uv run run-dashboard --data-dir data --run-date 2026-06-18
```

See [`investing/README.md`](investing/) and [`investing/docs/demo-slice.md`](investing/docs/demo-slice.md).

### Tech stack (investing)

* **Language:** Python 3.11+ · **Deps:** uv workspace ([ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md))
* **Data:** SimFin bulk · **Libs:** pandas, simfin, yfinance, streamlit, mlflow-skinny

---

## Credit (next)

Application **CSS**: public demo data → application mart → scoring → rank by default risk. Specs and code land under [`credit/`](credit/).

---

## Roadmap (portfolio)

1. **Credit** — chapter 6 OptBinning scorecard, monitoring, explainability (as scheduled).
2. **Tooling** — Domain deps / CI matrix (#183) after uv workspace ([#182](https://github.com/JLaborda/SmartWealthAI/issues/182), [ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md)).
3. **`platform/`** — Terraform / AWS; orchestrator choice open (Airflow vs EventBridge/ECS vs Prefect).
4. Optional: Spec Kit (#178); fraud module.

Phase 2 Quantitative Value (as production investing path) is **not** in active execution ([ADR-0003](docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`).

---

## How this repo is built

Specs in Git (`investing/docs/`, `credit/docs/`, ADRs, CONTEXT) drive implementation — **spec-driven development** with Cursor agents. Decisions land in Markdown first; code follows the matching feature doc. See [`AGENTS.md`](AGENTS.md) and [`docs/README.md`](docs/README.md).
