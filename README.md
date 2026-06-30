# 📈 SmartWealthAI

[![Tests](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml/badge.svg)](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/JLaborda/SmartWealthAI?branch=main&label=coverage)](https://codecov.io/gh/JLaborda/SmartWealthAI)

**A quantitative value-investing MVP: Greenblatt-style ranking on US equities.**

*Status: MVP spec refinement — [June 30 demo slice](docs/mvp/demo-slice.md) is the current delivery target.*

## Project vision

SmartWealthAI is a modular quantitative value investing system: SimFin fundamentals, point-in-time correctness, explainable ROC/EY ranking, and a Streamlit dashboard. The full architecture (backtest, sell-watch, paper trading) is the north star; the demo slice ships a narrower vertical first.

Canonical specs: [`docs/mvp/`](docs/mvp/) · Ubiquitous language: [`CONTEXT.md`](CONTEXT.md) · ADRs: [`docs/adr/`](docs/adr/)

## Tech stack

* **Language:** Python 3.11+
* **Environment & Dependencies:** Poetry
* **Data (demo):** SimFin bulk fundamentals and `shareprices/latest` (`simfin`)
* **Data (phase 2):** `yfinance` and free vendor fallbacks for prices / personal NAV
* **Core libraries:** `pandas`, `simfin`, `yfinance`, `requests` (SEC spike: `edgartools` — frozen)
* **MVP specs:** `docs/mvp/` (architecture + per-module features)

## 🚀 Quickstart

1.  **Install dependencies:**
    ```bash
    poetry install
    ```

2.  **Run tests (with coverage summary):**
    ```bash
    make test
    ```

3.  **Demo slice docs** — start here before coding:
    [`docs/mvp/demo-slice.md`](docs/mvp/demo-slice.md)

4.  **SimFin demo raw download:**
    ```bash
    export SIMFIN_API_KEY="<from user secrets>"
    poetry run download-simfin
    ```

    Guide: [`docs/mvp/guides/download-simfin.md`](docs/mvp/guides/download-simfin.md).

5.  **Demo dashboard** (after `score-universe` for a `run_date`):

    ```bash
    poetry run run-dashboard --data-dir data --run-date 2026-06-18
    ```

    Spec: [`docs/mvp/features/dashboard-reporting.md`](docs/mvp/features/dashboard-reporting.md).

6.  **SEC fundamentals spike (frozen, phase 2):**
    ```bash
    export SEC_IDENTITY="Your Name your@email.com"
    poetry run download-fundamentals --universe dow30
    ```

    Guide: [`docs/mvp/guides/download-fundamentals.md`](docs/mvp/guides/download-fundamentals.md).

## Roadmap

See [`docs/mvp/demo-slice.md`](docs/mvp/demo-slice.md) for the **June 30, 2026** delivery target and [`docs/mvp/architecture/architecture.md`](docs/mvp/architecture/architecture.md) for the full MVP north star.

### Demo slice (current)

- [ ] SimFin bulk ETL → raw + curated fundamentals
- [ ] US universe (SimFin minus banks / insurers / utilities)
- [ ] ROC + EY ranking → top-30 equal-weight portfolio
- [x] Streamlit dashboard (Overview, Ranking, Portfolio)
- [ ] MLflow run logging

### Phase 2 (after demo)

- Historical S&P 500 universe, permanent loss filter, backtesting
- Sell-watch, paper trading, SEC EDGAR normalizer (optional PIT upgrade)
- Corroborative signals, unstructured data, portfolio evolution