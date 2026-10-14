# Product backlog (informal)

Informal ideas from the product owner. Each item should eventually map to one or more [feature specs](features/) and [architecture.md](../architecture/architecture.md). Notion tasks should reference the relevant spec path.

| # | Idea | Likely MVP feature(s) |
| --- | --- | --- |
| 1 | Detect financial problems with holdings in my portfolio | [sell-watch.md](features/sell-watch.md), [permanent-loss-filter.md](features/permanent-loss-filter.md), [dashboard-reporting.md](features/dashboard-reporting.md) |
| 2 | Track portfolio evolution over time and compare to benchmarks (e.g. S&P 500) | [dashboard-reporting.md](features/dashboard-reporting.md), [backtesting.md](features/backtesting.md) |
| 3 | AI-assisted detector for undervalued stocks (Peter Lynch filters, Magic Formula) | [cheap-stocks.md](features/cheap-stocks.md), [high-quality-stocks.md](features/high-quality-stocks.md), [universe-construction.md](features/universe-construction.md) |
| 4 | Diversification analysis beyond sector labels (clustering in growth vs contraction regimes) | [corroborative-signals.md](features/corroborative-signals.md), [dashboard-reporting.md](features/dashboard-reporting.md) — may need a future spec |
| 5 | Detect overvalued positions where selling or trimming may make sense | [sell-watch.md](features/sell-watch.md), [cheap-stocks.md](features/cheap-stocks.md) |
| 6 | Rebalancing guidance (owner questions whether rebalance fits buy-cheap / sell-dear philosophy) | [architecture.md](../architecture/architecture.md) (annual rebalance decision), [broker-execution.md](features/broker-execution.md) |

## Priority

Ordering is not fixed here. During MVP planning, promote items into feature specs with acceptance criteria before implementation.
