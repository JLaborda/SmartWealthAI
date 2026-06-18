# SmartWealthAI

Ubiquitous language for the quantitative value-investing MVP. Canonical formulas and acceptance criteria live in `docs/mvp/`; this file is the concise vocabulary agents and humans share. Extend via `/grill-with-docs` when terms are resolved.

## Language

**Run date**:
The pipeline decision date (e.g. daily batch). Scoring, universe, and filters are keyed to this date.
_Avoid_: as-of date (reserved for filing availability), execution date

**As-of date**:
When a fundamental fact became publicly knowable. MVP: SimFin **Publish Date**; restatements use **Restated Date** as a new `version_id`; missing publish date → conservative `Report Date + lag` and **review queue**. Historical queries use `as_of_date <= run_date`.
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
Investable tickers for a run date. **June 30 demo:** all SimFin US companies minus banks/insurers/utilities (`IndustryId` exclusions + bank/insurance sanity check). **Phase 2:** historical S&P 500 constituents including delisted names. Spec: `docs/mvp/features/universe-construction.md`.
_Avoid_: watchlist, portfolio, benchmark index today

**Industry classification**:
Provider-assigned industry code used to apply sector hard exclusions (banks, insurers, utilities). MVP source: SimFin `IndustryId` on the company record; exclusions maintained in `data/reference/simfin_industry_exclusions.csv` with optional sanity check against SimFin bank/insurance statement datasets.
_Avoid_: SIC code (deferred with SEC ETL to phase 2), GICS, naive sector label from prices

**Sector hard exclusion (banks / insurers / utilities)**:
Hard exclusion because their financial statements are not comparable to industrial companies under Greenblatt ROC and EY—different line items, balance-sheet economics, and (for utilities) regulated returns. Not because SimFin lacks data; SimFin uses separate templates for banks and insurers.
_Avoid_: penalize, down-rank, “low quality score” for financials

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
Operating income before interest and taxes; **TTM** in MVP (Magic Formula scoring). Sourced from curated fundamentals (`formula_version = v1`).
_Avoid_: net income, EBITDA (unless a future spec says otherwise)

**Fundamentals periodicity (MVP)**:
Income and cash-flow statements use SimFin **TTM**; balance sheet uses the latest **quarterly** snapshot with `as_of_date <= run_date`. Annual-only series are not used for live scoring in MVP.
_Avoid_: mixing balance-sheet TTM into ROC denominators, using annual income for ranking between rebalance dates

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
Target long-only holdings from the pipeline; **June 30 demo:** top 30 names by combined rank, equal-weight only, market-cap tie-break on ranks. No watchlist in demo slice. Paper-traded in full MVP (phase 2).
_Avoid_: personal portfolio, watchlist (demo slice)

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
Rolling train/validation windows (3–5 years) over 20+ years of PIT data; annual rebalance. Spec: `docs/mvp/features/backtesting.md`. **Deferred to phase 2** for the June 30 demo MVP; demo slice stops at ranked model portfolio + dashboard.
_Avoid_: single in-sample fit, peeking at hold-out (when backtest ships)

**Block bootstrap**:
Monte Carlo that resamples contiguous multi-month blocks of real joint price/fundamental history.
_Avoid_: synthetic generative fundamentals (out of MVP)

**Raw zone / curated zone**:
Immutable provider responses vs normalized parquet consumed by scoring. Data lake: S3 + DuckDB. MVP: store SimFin bulk files verbatim in raw for every variant the pipeline downloads (TTM income/cashflow, quarterly balance); curated zone holds only what scoring consumes today. **Curated fundamentals schema is provider-agnostic** (`ebit`, `total_assets`, `as_of_date`, etc.)—SimFin and future SEC normalizers must emit the same contract.
_Avoid_: single “database” without lineage, SimFin-native column names in curated, normalizing annual/quarterly income in curated before QV needs it

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

Resolved scope cuts (see ADRs and [`docs/mvp/demo-slice.md`](docs/mvp/demo-slice.md)):

- **June 30 demo MVP:** SimFin bulk US → raw → normalizer → **universe (US market)** → ROC/EY → combined rank → top-30 EW model portfolio → Streamlit dashboard. No permanent loss filter, backtest, sell-watch, or paper trading in this slice.
- SEC ETL spike (`sec_client`, `edgartools_client`, `download-fundamentals`) is **frozen** in repo for phase 2; demo pipeline uses SimFin only (**free tier**, bulk download + ~weekly refresh); prices from yfinance.
- **Phase 2 (Quantitative Value):** will need multi-period fundamentals (not only TTM snapshots)—lake design should not block adding annual/quarterly income history later.

Terminology reminders:

- “Cheap” means high **EY**, not low P/E—use **EY rank** in issues and code names.
- “Quality” means high **ROC**, not ESG or subjective moat—use **ROC rank**.
- “Value trap” in specs means negative EBIT routed to **review queue**, not a separate score.
- MVP specs in `docs/mvp/` remain canonical until an ADR or architecture decision supersedes them; update `CONTEXT.md` when `/grill-with-docs` resolves a term conflict.
