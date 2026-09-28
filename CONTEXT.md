# SmartWealthAI

Ubiquitous language for the quantitative value-investing MVP. Canonical formulas and acceptance criteria live in `spec/`; this file is the concise vocabulary agents and humans share. Extend via `/grill-with-docs` when terms are resolved.

## Language

**Run date**:
The pipeline decision date (e.g. daily batch). Scoring, universe, and filters are keyed to this date.
_Avoid_: as-of date (reserved for filing availability), execution date

**Run-date share price (demo)**:
Closing price on or before the run date from SimFin bulk `shareprices/latest`, joined to the universe by ticker. Used for market cap (`shares_outstanding × adj_close`) in ROC tie-break and EY. **`price_date` may lag `run_date` by up to ~30 days** on the SimFin free tier; acceptable for the June demo. Full daily history (`shareprices/daily`) and alternate vendors (e.g. yfinance) are phase 2.
_Avoid_: Yahoo as canonical price when the universe is SimFin; requiring same-day prices in the demo pipeline

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
Investable tickers for a run date. **June 30 demo:** all SimFin US companies minus banks/insurers/utilities (`IndustryId` exclusions + bank/insurance sanity check). **Phase 2:** historical S&P 500 constituents including delisted names. Spec: `spec/features/011-universe-construction/spec.md`.
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
Hard exclusion for fraud or bankruptcy/distress risk before any score. Spec: `spec/features/008-permanent-loss-filter/spec.md`.
_Avoid_: risk score, stop-loss, drawdown rule

**Confirmed fraud signals**:
Structural or event-based fraud evidence from filings or regulators, such as recent restatements, repeated auditor changes, late-filer notices, or SEC enforcement actions. These are distinct from statistical manipulation models. Spec: `spec/features/008-permanent-loss-filter/spec.md`.
_Avoid_: using Beneish M-Score as if it were confirmed fraud

**Manipulation risk**:
Statistical risk that reported earnings or fundamentals are being managed or distorted. In phase 2, this starts with **Beneish M-Score** and may later include other forensic models. It is not the same as confirmed fraud. Spec: `spec/features/008-permanent-loss-filter/spec.md`.
_Avoid_: treating manipulation risk as proof of fraud

**Beneish unavailable**:
A company at a run date where **Beneish M-Score** cannot be computed (missing multi-period inputs or invalid derived ratios). **Fail-open** while fundamentals coverage is incomplete: route to **review queue** and allow pass through the manipulation screen. **Fail-closed** once multi-period ETL coverage is sufficient (default **≥95%** of the universe scorable on a run date): hard-exclude names that cannot be scored. Threshold versioned in `config/permanent_loss/`.
_Avoid_: treating missing Beneish as confirmed clean, silent pass without review queue

**Beneish M-Score**:
Classic 8-variable forensic accounting model that estimates **manipulation risk** from multi-period fundamentals. Gray/Carlisle *Quantitative Value* Ch. 3 labels the same model **PROBM** (probability of manipulation); in this repo the canonical name is **Beneish M-Score** (`beneish_score.py`). Coefficients versioned under `config/permanent_loss/beneish_v1.yaml`. In QV, the worst tail is hard-excluded via the **forensic bottom-percentile gate**, not an absolute academic cutoff.
_Avoid_: treating PROBM as a separate production model from Beneish, calling it confirmed fraud

**Forensic bottom-percentile gate**:
Cross-sectional hard exclusion of the worst manipulation-risk tail among forensic survivors on a run date. Phase 2a: bottom 5% by **Beneish M-Score** (`FRD_BENEISH_BOTTOM_PCT`) and bottom 5% by **COMBOACCRUAL** (`FRD_COMBOACCRUAL_BOTTOM_PCT`). No absolute academic cutoffs in the QV production path.
_Avoid_: M-Score > −1.78 as the production cutoff, time-series percentile across history

**Scaled total accruals (STA)**:
Accrual-flow manipulation signal from *Quantitative Value* Ch. 3: `(net income - operating cash flow) / total assets`. Higher STA → higher manipulation risk. Implemented in `accrual_scores.py`; pairs with **SNOA** in **COMBOACCRUAL**.
_Avoid_: conflating STA with Beneish M-Score

**Scaled net operating assets (SNOA)**:
Accrual-stock manipulation signal from *Quantitative Value* Ch. 3: `(operating assets - operating liabilities) / lagged total assets` (falls back to current total assets when prior period missing). Higher SNOA → higher manipulation risk. Implemented in `accrual_scores.py`.
_Avoid_: treating SNOA as a distress/bankruptcy model

**COMBOACCRUAL**:
Average cross-sectional percentile of **STA** and **SNOA** on a run date. Bottom 5% hard-excluded via `FRD_COMBOACCRUAL_BOTTOM_PCT` (`comboaccrual_gate_v1.yaml`).
_Avoid_: averaging raw STA/SNOA values without cross-sectional percentiles

**Forensic model fusion (phase 2b)**:
Post–phase 2a approach: first add book-faithful **separate bottom-5% gates** per forensic measure (COMBOACCRUAL, Beneish/PMAN, PFD or aligned distress model); only then experiment with **embedding / ML fusion** if backtests show incremental value without sacrificing explainability.
_Avoid_: jumping to ML fusion before individual gates are baseline-tested

**Probability of financial distress (PFD)**:
Campbell et al. logit model from *Quantitative Value* Ch. 3; estimates 12-month distress risk from market and balance-sheet inputs. **Backlog (phase 2b):** bottom-5% gate alongside existing **`BK_*` hard rules** (both kept; overlap measured in backtest before trimming).
_Avoid_: conflating PFD with manipulation risk (STA/SNOA/Beneish) or treating PFD as confirmed fraud

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
`EBIT / (Net Working Capital + Net Fixed Assets)`. Quality factor for the **Magic Formula benchmark**; higher is better; cross-sectional **ROC rank** (1 = best). Spec: `spec/features/007-high-quality-stocks/spec.md`.
_Avoid_: using ROC rank alone as production quality in Phase 2 — see **FS-Score**

**Net working capital (NWC)**:
`max(Current Assets − Excess Cash − Current Liabilities + Short-Term Debt, 0)` per versioned Greenblatt-style config. **v1:** excess cash uses curated `cash` (SimFin cash + cash equivalents + short-term investments — same field as EV).
_Avoid_: total working capital without the excess-cash adjustment

**Earnings yield (EY)**:
`EBIT / Enterprise Value`. Cheapness factor for the **Magic Formula benchmark**; higher is cheaper; cross-sectional **EY rank** (1 = cheapest). Spec: `spec/features/003-cheap-stocks/spec.md`.
_Avoid_: using EY rank alone as production cheapness in Phase 2 — see **value pool**

**Enterprise value (EV)**:
`Market Cap + Total Debt + Preferred Equity + Minority Interest − Cash`. **v1:** cash is SimFin cash + cash equivalents + short-term investments (curated `cash`).
_Avoid_: market cap alone as “value”

**Combined rank**:
Sum of ROC rank and EY rank; lower is better. Used for **Magic Formula replica** benchmark portfolio selection and sell-watch opportunity cost in the demo path. **Not** production ranking after Phase 2 — see **QV funnel rank**.
_Avoid_: average of ranks, z-score blend (not MVP)

**Quantitative Value (QV)**:
Production scoring methodology (Gray/Carlisle): forensic hard exclusion → EBIT/TEV value pool → FS-Score quality screen → concentrated model portfolio. Spec: `spec/features/013-quantitative-value/spec.md`.
_Avoid_: conflating QV with the June 30 demo Magic Formula path

**FS-Score**:
10-point Financial Strength Score (Gray/Carlisle variant): sum of binary profitability, stability, and operational-improvement signals (0–10). **Production quality** factor applied within the **value pool**. Spec: `spec/features/013-quantitative-value/spec.md`.
_Avoid_: Piotroski F-Score (different components), subjective ESG quality

**EBIT/TEV (production value metric)**:
`EBIT / Enterprise Value` using the same EV definition as **Earnings yield**. Cross-sectional rank among forensic survivors selects the **value pool** (top decile ~10%). Distinct from MF **EY rank** used in the benchmark path.
_Avoid_: treating EY rank and value-pool membership as interchangeable

**Value pool**:
Names surviving forensic screening that rank in the top decile (~10%) by **EBIT/TEV** on a run date. **Production cheapness** is membership in this pool, not MF **EY rank** alone.
_Avoid_: full universe, watchlist, final model portfolio

**QV funnel rank**:
Order within the **value pool** after the FS-Score quality screen; lower rank number = higher FS-Score (with market-cap tie-break). Drives production **model portfolio** selection (~50 names). Supersedes **combined rank** for production.
_Avoid_: combined rank, ROC rank, EY rank in Phase 2 production scoring

**Magic Formula replica**:
Benchmark portfolio using ROC, EY, combined rank, universe, and annual rebalance — same formulas as the June 30 demo slice. Used to gate backtest pass vs strategy Sharpe. **Not** production scoring after Phase 2.
_Avoid_: live Greenblatt fund, generic “value factor”, production scoring path

**Cross-sectional rank**:
Rank across all passing companies on one run date. Not comparable across dates without re-running the pipeline.
_Avoid_: time-series rank, percentile across history

**Formula version**:
Version id for ROC, EY, or filter rules so runs and backtests stay reproducible.
_Avoid_: “latest formula”, implicit default

**Model portfolio**:
Target long-only holdings from the pipeline. **June 30 demo:** top 30 names by combined rank, equal-weight, market-cap tie-break. **Phase 2 production:** top ~50 names by **QV funnel rank**, equal-weight (configurable cap). Paper-traded in full MVP (phase 2).
_Avoid_: personal portfolio, watchlist (demo slice)

**Watchlist**:
Ranked candidates broader than current holdings; may enter the model portfolio on rebalance.
_Avoid_: universe, model portfolio

**Paper trading**:
Simulated orders only; no real capital in the MVP.
_Avoid_: live trading, shadow trading with real broker

**Sell-watch**:
Daily monitor of model holdings for quality drop, fraud/bankruptcy, overvaluation, or opportunity cost; emits signals, no auto-execution. Spec: `spec/features/010-sell-watch/spec.md`.
_Avoid_: stop-loss, trailing stop (deferred)

**Sell signal**:
Recommendation to exit a holding; requires explicit user confirmation before order build in the MVP.
_Avoid_: auto-sell, trim (deferred state)

**Walk-forward backtest**:
Rolling train/validation windows (3–5 years) over 20+ years of PIT data; annual rebalance. Spec: `spec/features/001-backtesting/spec.md`. **Deferred to phase 2** for the June 30 demo MVP; demo slice stops at ranked model portfolio + dashboard.
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

- **June 30 demo:** A **run date** drives **universe** → **ROC** and **EY** ranks → **combined rank** → **model portfolio** (30 names)
- **Phase 2 production:** A **run date** drives **universe** → **permanent loss filter** / forensic screen → **value pool** (EBIT/TEV decile) → **FS-Score** → **QV funnel rank** → **model portfolio** (~50 names)
- **As-of date** tags each fundamental row; PIT queries filter `as_of_date <= run_date`
- **Magic Formula replica** is the strategy’s primary benchmark comparator for Sharpe pass/fail; uses **combined rank**, not **QV funnel rank**
- **Watchlist** superset of names that may enter the **model portfolio** on rebalance (phase 2)
- **Sell-watch** evaluates only the **model portfolio**, not the user’s personal portfolio

## Flagged ambiguities

Resolved scope cuts (see ADRs and [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md)):

- **June 30 demo MVP:** SimFin bulk US → raw → normalizer → **universe (US market)** → ROC/EY → combined rank → top-30 EW model portfolio → Streamlit dashboard. No permanent loss filter, backtest, sell-watch, or paper trading in this slice.
- SEC ETL spike (`sec_client`, `edgartools_client`, `download-fundamentals`) is **frozen** in repo for phase 2; demo pipeline uses SimFin bulk for fundamentals and run-date prices (`shareprices/latest`).
- **Phase 2 (Quantitative Value):** production scoring follows the QV funnel (`spec/features/013-quantitative-value/spec.md`); MF ROC/EY/combined rank remain benchmark-only. Multi-period fundamentals required for FS-Score and Beneish ([#87](https://github.com/JLaborda/SmartWealthAI/issues/87)).

Terminology reminders:

- **June 30 demo:** “Cheap” means high **EY rank**; “quality” means high **ROC rank**; portfolio uses **combined rank**.
- **Phase 2 production:** “Cheap” means **value pool** membership (top EBIT/TEV decile); “quality” means high **FS-Score**; portfolio uses **QV funnel rank**.
- “Value trap” in specs means negative EBIT routed to **review queue**, not a separate score.
- MVP specs in `spec/` remain canonical until an ADR or architecture decision supersedes them; update `CONTEXT.md` when `/grill-with-docs` resolves a term conflict.
