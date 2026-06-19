---
status: accepted
---

# SimFin as MVP fundamentals source (SEC ETL deferred)

For the June 30 demo and the near-term MVP pipeline, US fundamentals and **run-date share prices** come from **SimFin** (free tier, bulk download via the `simfin` Python package), not SEC EDGAR. Demo prices use SimFin bulk `shareprices/latest` joined to the universe by ticker. The existing SEC spike (`sec_client`, `edgartools_client`, `download-fundamentals`) stays in the repo **frozen** for phase 2; `yfinance` remains a possible fallback for phase 2 backtests and personal NAV, not the demo pipeline.

**Why:** SEC ETL complexity and rate limits were blocking progress on the scoring pipeline. SimFin provides standardized income, balance, and cash-flow statements with `Publish Date` / `Restated Date` for point-in-time queries, ~20 years of US history on the free tier, and a separate industry taxonomy—enough to ship a Magic Formula demo by end of June.

**Trade-offs:** `as_of_date` uses SimFin `Publish Date` (not EDGAR acceptance). Phase 2 SEC ingestion may require a reconciliation or re-backtest. SimFin free-tier datasets refresh roughly weekly, which is acceptable for annual-rebalance logic but not for intraday freshness.

**Considered:** Continue with SEC `companyfacts` only (rejected for June deadline); paid vendors Bloomberg/FactSet (out of budget).

**Consequences:** Update `etl-data-lake.md` and `universe-construction.md`; add SimFin connector + normalizer; keep `curated/fundamentals` schema provider-agnostic so scoring modules do not change.
