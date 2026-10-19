# 📈 SmartWealthAI

[![Tests](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml/badge.svg)](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/JLaborda/SmartWealthAI?branch=main&label=coverage)](https://codecov.io/gh/JLaborda/SmartWealthAI)

**Portfolio monorepo for finance engineering:** distinct domains a manager can spot at a glance.

*Portfolio release **v0.2.0** — Credit CSS demo slice + Spec Kit + uv workspace; Investing Magic Formula demo remains shipped.*

| Domain | Path | Status |
| --- | --- | --- |
| **Investing** (Magic Formula / value screening) | [`investing/`](investing/) | Demo slice shipped (portfolio **v0.2.0**) |
| **Credit** — CSS (Credit Scoring System) | [`credit/`](credit/) | Demo slice shipped — mart, WOE/XGB, FastAPI, PSI, doctor (portfolio **v0.2.0**) |
| **Fraud** | `fraud/` | Not started |
| **Platform** (AWS / Terraform) | [`platform/`](platform/) | Ephemeral Fargate CSS serve demo (stretch) |

Map & relationships: [`CONTEXT-MAP.md`](CONTEXT-MAP.md) · Investing glossary: [`investing/CONTEXT.md`](investing/CONTEXT.md) · Credit glossary: [`credit/CONTEXT.md`](credit/CONTEXT.md)

---

## Investing (shipped)

Greenblatt-style ranking on US equities: SimFin → PIT lake → ROC + EY → top-30 EW model portfolio → Streamlit + MLflow.

*Code:* [`investing/src/investing/`](investing/src/investing/) · Dashboard: [`investing/apps/dashboard/`](investing/apps/dashboard/) · Specs: [`investing/docs/`](investing/docs/) · Living Spec Kit: [`specs/006-june-demo-slice/`](specs/006-june-demo-slice/spec.md)

### Quickstart (investing demo)

```bash
uv sync
export SIMFIN_API_KEY="<from user secrets>"
uv run run-demo-pipeline --run-date 2026-06-18
uv run run-dashboard --data-dir data --run-date 2026-06-18
```

See [`investing/README.md`](investing/) and [`specs/006-june-demo-slice/spec.md`](specs/006-june-demo-slice/spec.md).

### Tech stack (investing)

* **Language:** Python 3.11+ · **Deps:** uv workspace ([ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md))
* **Data:** SimFin bulk · **Libs:** pandas, simfin, yfinance, streamlit, mlflow-skinny

---

## Credit (shipped demo slice)

Application **CSS**: public demo data → application mart → WOE/IV + XGBoost → FastAPI `/score` + `/drivers` → PSI + `credit-css doctor`. Specs and code under [`credit/`](credit/); living Spec Kit: [`specs/013-css-chapter5-mart-and-scoring/`](specs/013-css-chapter5-mart-and-scoring/spec.md).

### Quickstart (credit demo)

```bash
uv sync
git lfs pull --include="credit/data/*"   # optional book sample
uv run credit-css doctor
# Friday rehearsal: credit/docs/guides/friday-demo.md
```

---

## Roadmap (portfolio)

1. **Credit** — chapter 6 OptBinning scorecard, deeper monitoring / explainability.
2. **`platform/`** — broader AWS cutover; orchestrator choice open (Airflow vs EventBridge/ECS vs Prefect).
3. Optional: fraud module.

Phase 2 Quantitative Value (as production investing path) is **not** in active execution ([ADR-0003](docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`).

---

## How this repo is built

Living Spec Kit specs under [`specs/`](specs/) (plus domain docs, ADRs, CONTEXT) drive implementation — **spec-driven development** with Cursor agents. Decisions land in Markdown first; code follows the matching feature doc. See [`AGENTS.md`](AGENTS.md) and [`docs/README.md`](docs/README.md).

Release notes: [CHANGELOG.md](CHANGELOG.md).
