# June 30 demo slice — simplest Magic Formula

**Status:** accepted (see [ADR-0002](../adr/0002-june-demo-scope-cut.md))  
**Target date:** 2026-06-30  
**North star:** Full MVP in [`architecture/architecture.md`](architecture/architecture.md) — this document defines only what ships first.

## Objective

Deliver a working, explainable Greenblatt-style Magic Formula pipeline on real US data: ingest fundamentals, rank the market, build a model portfolio, show results in Streamlit. No historical validation or execution in this slice.

## In scope

| Step | Module / spec | Notes |
| --- | --- | --- |
| 1 | SimFin ETL | [`etl-data-lake.md`](features/etl-data-lake.md) — bulk US download, raw zone, SimFin normalizer |
| 2 | Universe | [`universe-construction.md`](features/universe-construction.md) — demo mode: SimFin US minus sector exclusions |
| 3 | Quality | [`high-quality-stocks.md`](features/high-quality-stocks.md) — ROC |
| 4 | Cheapness | [`cheap-stocks.md`](features/cheap-stocks.md) — Earnings Yield |
| 5 | Ranking | Combined rank = ROC rank + EY rank (lower is better); tie-break ascending market cap |
| 6 | Model portfolio | Top **30** names, **equal-weight** only |
| 7 | Dashboard | [`dashboard-reporting.md`](features/dashboard-reporting.md) — ranking table, portfolio, per-name explainability |
| 8 | MLflow | Log each pipeline run (params, scoring metrics, portfolio artifact) — `src/smartwealthai/mlflow_run_logging.py`, wired in `score-universe` ([#61](https://github.com/JLaborda/SmartWealthAI/issues/61)) |

## Out of scope (phase 2)

- Permanent loss filter ([`permanent-loss-filter.md`](features/permanent-loss-filter.md))
- Backtesting and crisis report ([`backtesting.md`](features/backtesting.md))
- Sell-watch ([`sell-watch.md`](features/sell-watch.md))
- Paper trading / broker ([`broker-execution.md`](features/broker-execution.md))
- Watchlist (ranking table in dashboard is enough)
- Corroborative signals, unstructured data, portfolio evolution (personal CSV)
- SEC EDGAR ETL (frozen spike remains in repo — [ADR-0001](../adr/0001-simfin-fundamentals-mvp.md))
- Historical S&P 500 universe with delisted names
- Score-weighted and risk-parity weighting

## Data sources

| Data | Source | Tier |
| --- | --- | --- |
| Fundamentals | SimFin bulk (`income` TTM, `balance` quarterly, `cashflow` TTM, `companies`, `industries`) | Free |
| Prices (demo) | SimFin bulk `shareprices/latest` | Free; same ticker namespace as universe |
| Prices (phase 2) | SimFin `shareprices/daily` or vendor fallback | Backtest and personal NAV |
| Industry exclusions | `data/reference/simfin_industry_exclusions.csv` + bank/insurance dataset sanity check | Versioned CSV |

## Pipeline diagram

```mermaid
flowchart LR
    SimFin["SimFin bulk US"] --> Raw["raw/simfin/"]
    Raw --> Norm["SimFin normalizer"]
    Raw --> SharePx["shareprices/latest"]
    Norm --> Fund["curated/fundamentals"]
    SharePx --> Prices["curated/prices"]
    Companies["SimFin companies + industries"] --> Uni["Universe (US − exclusions)"]
    Fund --> Uni
    Uni --> ROC["ROC rank"]
    Uni --> EY["EY rank"]
    Prices --> ROC
    Prices --> EY
    Fund --> ROC
    Fund --> EY
    ROC --> Rank["Combined rank"]
    EY --> Rank
    Rank --> Port["Top 30 EW portfolio"]
    Port --> Dash["Streamlit dashboard"]
    Port --> MLflow["MLflow run"]
```

## Key decisions (closed for demo)

| Topic | Decision |
| --- | --- |
| Backfill | Full SimFin US bulk per dataset variant; normalizer filters to universe tickers |
| `as_of_date` | SimFin `Publish Date`; restatements → new `version_id` with `Restated Date`; missing publish → `Report Date + lag` → review queue |
| Fundamentals periodicity | Income/cashflow **TTM**; balance sheet **quarterly** (latest PIT row) |
| Raw vs curated | Raw verbatim for downloaded variants; curated minimal (provider-agnostic schema) |
| Universe | All SimFin `market=us` companies minus banks/insurers/utilities (`IndustryId` CSV + bank/insurance sanity check) |
| Share prices | SimFin `shareprices/latest`; `price_date` may lag `run_date` by ~30 days (free tier) — OK for demo |
| Portfolio | Top 30, equal-weight, market-cap tie-break on ranks |
| SEC code | Frozen, not called by demo pipeline |

## Acceptance criteria

- [x] One command (or Prefect flow) runs the full demo pipeline for a `run_date`.
- [x] Dashboard shows combined rank, ROC/EY inputs, and top-30 portfolio with explanations.
- [ ] Every curated fundamental row has `as_of_date <= run_date` when queried PIT.
- [ ] No bank/insurer/utility from the exclusion list appears in the ranked universe.
- [x] MLflow run exists with portfolio parquet artifact and git commit SHA tag.
- [x] Hermetic CI tests do not call SimFin or yfinance live.

## After the demo (phase 2 order)

Per [`prds/phase2/prd.md`](prds/phase2/prd.md) — **Quantitative Value is production scoring**; Magic Formula (ROC + EY + combined rank) remains **benchmark-only**.

1. **QV feature spec** — [`quantitative-value.md`](features/quantitative-value.md) (canonical funnel; blocks scoring implementation)  
2. Multi-period fundamentals + daily prices (FS-Score YoY deltas, backtest NAV)  
3. Forensic evaluator + Beneish bottom-5% gate (extends [`permanent-loss-filter.md`](features/permanent-loss-filter.md))  
4. **QV funnel** — EBIT/TEV value decile → FS-Score → ~50-name EW model portfolio  
5. Light backtest (5–10 years, annual rebalance) vs S&P 500 CW + MF replica  
6. Cloud pipeline (S3 lake, ECS, MLflow S3 artifacts)  
7. Sell-watch with QV-adapted triggers + dashboard  
8. Historical S&P 500 universe (delisted names) + full backtest (20+ years, walk-forward, Sharpe gate)  
9. SEC EDGAR normalizer (optional PIT upgrade)  
10. Paper trading + broker (after passing full backtest)
