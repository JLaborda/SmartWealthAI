# Product backlog (informal)

Informal ideas from the product owner. Each item should eventually map to one or more [feature specs](features/) and [mission.md](../constitution/mission.md). GitHub issues should reference the relevant spec path.

| # | Idea | Likely MVP feature(s) |
| --- | --- | --- |
| 1 | Detect financial problems with holdings in my portfolio | [sell-watch.md](../010-sell-watch/spec.md), [permanent-loss-filter.md](../008-permanent-loss-filter/spec.md), [dashboard-reporting.md](../005-dashboard-reporting/spec.md) |
| 2 | Track portfolio evolution over time and compare to benchmarks (e.g. S&P 500) | [dashboard-reporting.md](../005-dashboard-reporting/spec.md), [backtesting.md](../001-backtesting/spec.md) |
| 3 | AI-assisted detector for undervalued stocks (Peter Lynch filters, Magic Formula) | [cheap-stocks.md](../003-cheap-stocks/spec.md), [high-quality-stocks.md](../007-high-quality-stocks/spec.md), [universe-construction.md](../011-universe-construction/spec.md) |
| 4 | Diversification analysis beyond sector labels (clustering in growth vs contraction regimes) | [corroborative-signals.md](../004-corroborative-signals/spec.md), [dashboard-reporting.md](../005-dashboard-reporting/spec.md) — may need a future spec |
| 5 | Detect overvalued positions where selling or trimming may make sense | [sell-watch.md](../010-sell-watch/spec.md), [cheap-stocks.md](../003-cheap-stocks/spec.md) |
| 6 | Rebalancing guidance (owner questions whether rebalance fits buy-cheap / sell-dear philosophy) | [mission.md](../constitution/mission.md) (annual rebalance decision), [broker-execution.md](../002-broker-execution/spec.md) |
| 7 | **Forensic model zoo (post–phase 2a), in order:** (1) STA, SNOA, COMBOACCRUAL; (2) **PFD** bottom-5% gate alongside `BK_*`; (3) EDGAR **confirmed fraud signals**; (4) embedding/ML fusion after gates are baseline-tested | [008-permanent-loss-filter](../features/008-permanent-loss-filter/spec.md), [013-quantitative-value](../features/013-quantitative-value/spec.md) |
| 8 | **Confirmed fraud signals from EDGAR** (restatements, auditor change, late filer, SEC enforcement) — wire when SEC ETL unfreezes | [008-permanent-loss-filter](../features/008-permanent-loss-filter/spec.md), [006-etl-data-lake](../features/006-etl-data-lake/spec.md) |
| 9 | **Embedding / ML fusion** of forensic model outputs (mathematical scores → combined manipulation-risk signal) — explore **after** separate bottom-5% gates (COMBOACCRUAL, PMAN, PFD) are baseline-tested in backtest | [008-permanent-loss-filter](../features/008-permanent-loss-filter/spec.md) |

## Priority

Ordering is not fixed here. During MVP planning, promote items into feature specs with acceptance criteria before implementation.
