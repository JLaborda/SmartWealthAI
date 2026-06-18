---
status: accepted
---

# June 30 demo slice — simplest Magic Formula vertical

The **June 30 deliverable** is a reduced vertical slice, not the full architecture vision. Pipeline: **SimFin ETL → universe (US market) → ROC/EY → combined rank → top-30 equal-weight model portfolio → Streamlit dashboard**. Permanent loss filter, backtesting, sell-watch, paper trading, watchlist, and corroborative/unstructured modules are **deferred to phase 2**.

**Why:** The project is behind schedule. The portfolio demo must show an explainable, end-to-end Magic Formula run on real data—not every MLOps and risk gate in the full spec.

**Trade-offs:** No backtest gate before orders (orders are out of scope anyway). Universe is all SimFin US companies minus banks/insurers/utilities—not historical S&P 500 with delisted names (survivorship bias mitigation waits for backtest phase). No permanent-loss filter in the demo path.

**Considered:** Full MVP including 20-year walk-forward backtest (rejected for June); demo + minimal backtest (rejected—user chose fastest path); Zipline for backtests (rejected—incompatible with Python 3.11, unmaintained, poor fit for fundamental annual rebalance).

**Consequences:** Documented in [`docs/mvp/demo-slice.md`](../mvp/demo-slice.md). Full feature specs remain the north star; modules marked deferred are unchanged in intent. MLflow logs **pipeline runs** in the demo; the `backtesting` experiment starts in phase 2.
