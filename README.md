# 📈 SmartWealthAI

[![Tests](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml/badge.svg)](https://github.com/JLaborda/SmartWealthAI/actions/workflows/pr-ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/JLaborda/SmartWealthAI?branch=main&label=coverage)](https://codecov.io/gh/JLaborda/SmartWealthAI)

**A quantitative value-investing MVP: Greenblatt-style ranking on US equities.**

*Status: **v0.1.0** — [June 30 demo slice](spec/constitution/roadmap.md) runnable from CLI (Poetry + SimFin API key).*

## Project vision

SmartWealthAI is a modular quantitative value investing system: SimFin fundamentals, point-in-time correctness, explainable ROC/EY ranking, and a Streamlit dashboard. The full architecture (backtest, sell-watch, paper trading) is the north star; the demo slice ships a narrower vertical first.

Canonical specs: [`spec/`](spec/) · Ubiquitous language: [`CONTEXT.md`](CONTEXT.md) · ADRs: [`spec/adr/`](spec/adr/)

## Tech stack

* **Language:** Python 3.11+
* **Environment & Dependencies:** Poetry
* **Data (demo):** SimFin bulk fundamentals and `shareprices/latest` (`simfin`)
* **Data (phase 2):** `yfinance` and free vendor fallbacks for prices / personal NAV
* **Core libraries:** `pandas`, `simfin`, `yfinance`, `requests` (SEC spike: `edgartools` — frozen)
* **MVP specs:** `spec/` (architecture + per-module features)

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
    [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md)

4.  **Run the full demo pipeline** (one command for a `run_date`):

    ```bash
    export SIMFIN_API_KEY="<from user secrets>"
    poetry run run-demo-pipeline --run-date 2026-06-18
    ```

    Individual stages (`download-simfin`, `normalize-simfin`, `build-universe`, `score-universe`, …) are also available. Guide: [`spec/guides/download-simfin.md`](spec/guides/download-simfin.md).

5.  **Demo dashboard** (after the pipeline for the same `run_date`):

    ```bash
    poetry run run-dashboard --data-dir data --run-date 2026-06-18
    ```

    Spec: [`spec/features/005-dashboard-reporting/spec.md`](spec/features/005-dashboard-reporting/spec.md).

6.  **SEC fundamentals spike (frozen, phase 2):**
    ```bash
    export SEC_IDENTITY="Your Name your@email.com"
    poetry run download-fundamentals --universe dow30
    ```

    Guide: [`spec/guides/download-fundamentals.md`](spec/guides/download-fundamentals.md).

## Roadmap

See [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md) for the **June 30, 2026** delivery target and [`spec/constitution/mission.md`](spec/constitution/mission.md) for the full MVP north star.

### Demo slice (v0.1.0)

- [x] SimFin bulk ETL → raw + curated fundamentals
- [x] US universe (SimFin minus banks / insurers / utilities)
- [x] ROC + EY ranking → top-30 equal-weight portfolio
- [x] End-to-end CLI (`run-demo-pipeline`)
- [x] Streamlit dashboard (Overview, Ranking, Portfolio)
- [x] MLflow run logging

See [CHANGELOG.md](CHANGELOG.md) for release notes.

### Phase 2 (after demo)

- Historical S&P 500 universe, permanent loss filter, backtesting
- Sell-watch, paper trading, SEC EDGAR normalizer (optional PIT upgrade)
- Corroborative signals, unstructured data, portfolio evolution