# SmartWealthAI

Ubiquitous language for the quantitative value-investing MVP. Canonical formulas and acceptance criteria live in `docs/mvp/`; this file is the concise vocabulary agents and humans share. Extend via `/grill-with-docs` when terms are resolved.

## Language

**Run date**:
The pipeline decision date (e.g. daily batch). Scoring, universe, and filters are keyed to this date.
_Avoid_: as-of date (reserved for filing availability), execution date

**As-of date**:
When a fundamental fact became publicly knowable—typically SEC EDGAR filing acceptance. Historical queries use `as_of_date <= run_date`.
_Avoid_: run date, report date, period end (unless explicitly the accounting period)

**Point-in-time (PIT)**:
Constraint that only data public on or before the run date may be used. Restatements keep the version known at each historical decision date.
_Avoid_: real-time fundamentals, latest restated series in backtests

**Look-ahead bias**:
Using future information in a historical simulation. Treated as a critical defect.
_Avoid_: data leakage, peeking

**Survivorship bias**:
Backtesting only companies that still exist today, overstating returns. Mitigated by historical S&P 500 constituents including delisted names.
_Avoid_: living-universe backtest

**Universe**:
Investable tickers for a run date—seeded from historical S&P 500 constituents, filtered to common US stocks, with banks/insurers/utilities excluded. Spec: `docs/mvp/features/universe-construction.md`.
_Avoid_: watchlist, portfolio, benchmark index today

**Hard exclusion**:
A company removed entirely from ranking (not a score penalty). Permanent loss and some universe rules are hard exclusions.
_Avoid_: penalize, down-rank, soft filter

**Permanent loss filter**:
Hard exclusion for fraud or bankruptcy/distress risk before any score. Spec: `docs/mvp/features/permanent-loss-filter.md`.
_Avoid_: risk score, stop-loss, drawdown rule

**Review queue**:
Rows flagged for human review—invalid denominators, missing inputs, negative EBIT for EY, etc.—stored under `curated/issues/`.
_Avoid_: silent drop, auto-fix without audit

**EBIT**:
Operating income before interest and taxes; TTM in MVP. Shared numerator for ROC and Earnings Yield (`OperatingIncomeLoss` from EDGAR for `formula_version = v1`).
_Avoid_: net income, EBITDA (unless a future spec says otherwise)

**Return on capital (ROC)**:
`EBIT / (Net Working Capital + Net Fixed Assets)`. Quality factor; higher is better; cross-sectional **ROC rank** (1 = best). Spec: `docs/mvp/features/high-quality-stocks.md`.
_Avoid_: ROE, ROIC (unless explicitly that metric)

**Net working capital (NWC)**:
`max(Current Assets − Excess Cash − Current Liabilities + Short-Term Debt, 0)` per versioned Greenblatt-style config.
_Avoid_: total working capital without the excess-cash adjustment

**Earnings yield (EY)**:
`EBIT / Enterprise Value`. Cheapness factor; higher is cheaper; cross-sectional **EY rank** (1 = cheapest). Spec: `docs/mvp/features/cheap-stocks.md`.
_Avoid_: dividend yield, earnings/price without EV

**Enterprise value (EV)**:
`Market Cap + Total Debt + Preferred Equity + Minority Interest − Cash and Equivalents`. Denominator for EY.
_Avoid_: market cap alone as “value”

**Combined rank**:
Sum of ROC rank and EY rank; lower is better. Used for portfolio selection and sell-watch opportunity cost.
_Avoid_: average of ranks, z-score blend (not MVP)

**Magic Formula replica**:
Canonical benchmark portfolio using the same ROC, EY, combined rank, universe, and annual rebalance as production. Used to gate backtest pass vs strategy Sharpe.
_Avoid_: live Greenblatt fund, generic “value factor”

**Cross-sectional rank**:
Rank across all passing companies on one run date. Not comparable across dates without re-running the pipeline.
_Avoid_: time-series rank, percentile across history

**Formula version**:
Version id for ROC, EY, or filter rules so runs and backtests stay reproducible.
_Avoid_: “latest formula”, implicit default

**Model portfolio**:
Target long-only holdings (15–30 names, max 10% per name) from the pipeline; paper-traded for tracking.
_Avoid_: personal portfolio, watchlist

**Watchlist**:
Ranked candidates broader than current holdings; may enter the model portfolio on rebalance.
_Avoid_: universe, model portfolio

**Paper trading**:
Simulated orders only; no real capital in the MVP.
_Avoid_: live trading, shadow trading with real broker

**Sell-watch**:
Daily monitor of model holdings for quality drop, fraud/bankruptcy, overvaluation, or opportunity cost; emits signals, no auto-execution. Spec: `docs/mvp/features/sell-watch.md`.
_Avoid_: stop-loss, trailing stop (deferred)

**Sell signal**:
Recommendation to exit a holding; requires explicit user confirmation before order build in the MVP.
_Avoid_: auto-sell, trim (deferred state)

**Walk-forward backtest**:
Rolling train/validation windows (3–5 years) over 20+ years of PIT data; annual rebalance. Spec: `docs/mvp/features/backtesting.md`.
_Avoid_: single in-sample fit, peeking at hold-out

**Block bootstrap**:
Monte Carlo that resamples contiguous multi-month blocks of real joint price/fundamental history.
_Avoid_: synthetic generative fundamentals (out of MVP)

**Raw zone / curated zone**:
Immutable provider responses vs normalized parquet consumed by scoring. Data lake: S3 + DuckDB.
_Avoid_: single “database” without lineage

**MLflow run**:
Logged experiment with parameters, metrics, and artifacts (watchlist, backtest report, commit SHA).
_Avoid_: ad-hoc snapshot without run id

## Relationships

- A **run date** drives **universe** → **permanent loss filter** → **ROC** and **EY** ranks → **combined rank** → **model portfolio**
- **As-of date** tags each fundamental row; PIT queries filter `as_of_date <= run_date`
- **Watchlist** superset of names that may enter the **model portfolio** on rebalance
- **Magic Formula replica** is the strategy’s primary benchmark comparator for Sharpe pass/fail
- **Sell-watch** evaluates only the **model portfolio**, not the user’s personal portfolio

## Flagged ambiguities

- “Cheap” means high **EY**, not low P/E—use **EY rank** in issues and code names.
- “Quality” means high **ROC**, not ESG or subjective moat—use **ROC rank**.
- “Value trap” in specs means negative EBIT routed to **review queue**, not a separate score.
- MVP specs in `docs/mvp/` remain canonical until an ADR or architecture decision supersedes them; update `CONTEXT.md` when `/grill-with-docs` resolves a term conflict.
