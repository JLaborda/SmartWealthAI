# Feature: Quantitative Value

## Implementation status

**planned**

## Delivery

**Phase:** phase 2 (production scoring replaces Greenblatt demo path)

## Objective

Implement the *Quantitative Value* funnel (Gray/Carlisle): forensic hard exclusion → top ~10% by EBIT/TEV among survivors → FS-Score on the value pool → ~50 equal-weight model portfolio. Magic Formula (ROC + EY) remains a **benchmark-only** path for backtest comparison, not production scoring.

## In scope

- QV funnel orchestrator invoked by `score-universe` (or successor CLI) for a `run_date`.
- Value screen: EBIT/TEV cross-sectional rank; keep top decile (~10%).
- Quality screen: 10-point FS-Score (binary components per Gray/Carlisle) on the value pool.
- Model portfolio: ~50 equal-weight names (configurable cap); default **50**.
- Stage-count metrics logged to MLflow; scored artifacts per funnel stage in curated lake.
- Forensic bottom-5% cross-sectional exclusion gate (QVAL-style) integrated with [`008-permanent-loss-filter`](../008-permanent-loss-filter/spec.md).
- Distinct `qv_*` vs `mf_*` code paths; production never calls MF combined rank.

## Out of scope

- Paper trading and broker execution.
- Full 20-year walk-forward backtest (see [`001-backtesting`](../001-backtesting/spec.md)).
- SEC EDGAR fraud rules that require EDGAR ETL (log `unavailable` until wired).
- Score-weighted or risk-parity portfolio construction.

## Inputs

| Input | Source | Notes |
| --- | --- | --- |
| Universe | `curated/universe/` | Sector exclusions upstream ([`011-universe-construction`](../011-universe-construction/spec.md)) |
| PIT fundamentals (multi-period) | `curated/fundamentals/` | Annual/quarterly for FS-Score and Beneish |
| Prices | `curated/prices/` | EV / market cap on `run_date` |
| Forensic exclusions | `curated/permanent_loss/` | Hard exclude before value screen |
| Run date | Pipeline parameter | Strict PIT: `as_of_date <= run_date` |

## Outputs

| Output | Path / target |
| --- | --- |
| Funnel stage counts | MLflow metrics |
| Value pool ranks | `curated/scores/value/` |
| FS-Score breakdown | `curated/scores/quality/` |
| Model portfolio | `curated/portfolio/run_date=<YYYY-MM-DD>/portfolio.parquet` |
| Review queue rows | `curated/issues/` for missing FS-Score / forensic inputs |

## Mermaid diagram

```mermaid
flowchart TD
    Uni["Universe"] --> Forensic["Forensic hard exclusion"]
    Forensic --> Value["Top ~10% EBIT/TEV"]
    Value --> FS["FS-Score on value pool"]
    FS --> Port["Top ~50 EW portfolio"]
    MF["MF benchmark path (ROC+EY)"] -.->|"backtest only"| Bench["Benchmark portfolios"]
```

## Expected flow

1. Load universe for `run_date`; apply sector exclusions (already done upstream).
2. Run forensic evaluator; drop hard exclusions and bottom-5% forensic percentile gate.
3. Rank survivors by EBIT/TEV; keep top decile (value pool).
4. Compute FS-Score (0–10) for each value-pool name; rank by score.
5. Select top ~50 names; equal-weight; write portfolio parquet + MLflow artifact.
6. Log stage counts: universe → forensic → value → quality → portfolio.

## Acceptance criteria

- [ ] `spec/features/013-quantitative-value/spec.md` exists with objective, scope, funnel stages, and acceptance criteria (this document).
- [ ] FS-Score components and forensic bottom-5% gate documented with formula versions.
- [ ] Portfolio size default (~50) and configurable cap recorded as a closed decision.
- [ ] `CONTEXT.md` updated with production QV terms (quality = FS-Score, cheap = value pool, QV funnel rank); MF terms marked benchmark-only.
- [ ] `spec/constitution/roadmap.md` "After the demo" section reflects QV-first production order.
- [ ] `score-universe` runs full QV funnel for a `run_date` when implementation completes ([#91](https://github.com/JLaborda/SmartWealthAI/issues/91)).
- [ ] Excluded names never appear in final portfolio; stage shrinkage monotonic on fixtures.

## Open questions

- **Closed:** Portfolio default size = **50** names, configurable via versioned QV config.

## Risks

- Multi-period fundamentals not available until ETL extension ([#87](https://github.com/JLaborda/SmartWealthAI/issues/87)) — funnel blocked until PIT history exists.
- FS-Score and Beneish need aligned fiscal-period joins; missing inputs must route to review queue, not silent drop.

## Related specs

- [`spec/prds/phase2/prd.md`](../../prds/phase2/prd.md) — parent PRD ([#85](https://github.com/JLaborda/SmartWealthAI/issues/85))
- [`../008-permanent-loss-filter/spec.md`](../008-permanent-loss-filter/spec.md) — forensic evaluator ([#89](https://github.com/JLaborda/SmartWealthAI/issues/89))
- [`../006-etl-data-lake/spec.md`](../006-etl-data-lake/spec.md) — multi-period ETL ([#87](https://github.com/JLaborda/SmartWealthAI/issues/87))
- [`../007-high-quality-stocks/spec.md`](../007-high-quality-stocks/spec.md) — MF ROC benchmark ([#92](https://github.com/JLaborda/SmartWealthAI/issues/92))
- [`../003-cheap-stocks/spec.md`](../003-cheap-stocks/spec.md) — MF EY benchmark ([#92](https://github.com/JLaborda/SmartWealthAI/issues/92))
- [`../005-dashboard-reporting/spec.md`](../005-dashboard-reporting/spec.md) — QV explainability ([#93](https://github.com/JLaborda/SmartWealthAI/issues/93))
