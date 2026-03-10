# 📈 SmartWealthAI

**A lightweight financial screener and portfolio management tool.**

*Status: Phase 1 / Sprint 0 (Proof of Concept)*

## 🎯 Project Vision
SmartWealthAI is being built iteratively with a strict Agile philosophy. The current focus is on establishing a simple, reliable data pipeline for core financial metrics, starting with a raw implementation of Joel Greenblatt's "Magic Formula".

Future iterations (Phase 3+) will introduce advanced Machine Learning capabilities, including AI Agents performing RAG over 10-K business annual reports, and interactive dashboards.

## 🛠️ Current Tech Stack
* **Language:** Python
* **Environment & Dependencies:** Poetry
* **Core Libraries:** `yfinance`, `pandas`

## 🚀 Quickstart

1.  **Install dependencies:**
    ```bash
    poetry install
    ```

2.  **Run the basic screener:**
    ```bash
    poetry run python main.py
    ```

## 🗺️ Roadmap (Agile Milestones)

### Phase 1: Core Mechanics (Current)
- [x] Project initialization (`poetry`).
- [x] Fetch basic metrics (P/E, ROE, ROA) via `yfinance` for a static portfolio.
- [ ] Implement mathematical ranking logic ("Magic Formula").
- [ ] CLI basic formatting.

### Phase 2: Scale & Structure (TBD)
- [ ] Expand universe of tickers.
- [ ] Basic data persistence (No DBs yet, maybe CSV/JSON).
- [ ] Modularize architecture.

### Phase 3: The "AI" in SmartWealthAI
- [ ] Introduce Machine Learning components.
- [ ] LLM integration: RAG over 10-K annual reports.
- [ ] Interactive Dashboard deployment.