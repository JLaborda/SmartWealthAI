# PRD: MVP Phase 2 — Quantitative Value, Cloud, Backtest, Sell-Watch

**Status:** Ready for implementation  
**Canonical architecture:** `spec/constitution/mission.md`  
**Prior delivery:** June 30 demo slice (`spec/constitution/roadmap.md`, ADR-0002)  
**Related specs:** ETL + data lake, permanent loss filter, backtesting, sell-watch, universe construction, dashboard reporting  
**Related PRDs:** CI/CD (`spec/prds/ci-cd/ci-cd-prd.md`)  
**Capacity assumption:** Solo developer, ~10–15 hours per week  
**Estimated calendar:** Phase 2a ~13–16 weeks; Phase 2b ~8–12 weeks (~5–7 months total)

---

## Problem Statement

The June 30 demo slice delivers a working Greenblatt-style Magic Formula pipeline (ROC + Earnings Yield → combined rank → top-30 equal-weight model portfolio) on local SimFin data with a Streamlit dashboard and MLflow file-store logging. That slice proves ingestion, point-in-time fundamentals, cross-sectional ranking, and explainability — but it is not the investor's target strategy, not deployed to AWS, not historically validated, and does not monitor holdings for thesis breaks.

The investor wants Phase 2 to:

1. **Replace production scoring** with the *Quantitative Value* methodology (Wesley R. Gray / Tobias Carlisle): forensic screens, value funnel (EBIT/TEV), quality funnel (FS-Score), and a concentrated model portfolio (~50 names).
2. **Run the pipeline in AWS** so daily scoring is independent of a developer laptop.
3. **Backtest the strategy** to judge whether it is worth following — starting with a light historical run, then expanding to the full architecture spec.
4. **Alert on sell conditions** when a holding's QV thesis deteriorates — without auto-execution or paper trading in this phase.

Without a single PRD tying these goals together, Phase 2 risks repeating the demo's scope creep in reverse: cloud work before the QV funnel exists, or backtests that still score ROC+EY while production claims to be Quantitative Value.

## Solution

Deliver Phase 2 in two increments:

### Phase 2a (core)

1. Extend the data lake for **multi-period fundamentals** and **daily prices** (5–10 year window) with point-in-time correctness preserved.
2. Implement **forensic / permanent-loss screening** including Beneish M-Score and the distress rules already specified, with a QVAL-style bottom-percentile gate on forensic models.
3. Replace the production scoring path with the **full QV funnel**: universe → forensic hard exclusion → top ~10% by EBIT/TEV → FS-Score on the value pool → top ~50 equal-weight model portfolio.
4. Keep **Magic Formula (ROC + EY + combined rank)** as a **benchmark module only** for backtest comparison — not production scoring.
5. Run a **light backtest** (5–10 years, annual rebalance, current SimFin US universe, S&P 500 CW + Magic Formula benchmarks) using a custom pandas/DuckDB engine (no Zipline).
6. Deploy **cloud phase 2a**: S3 data lake + artifacts, ECS Fargate Spot daily cron, Secrets Manager, MLflow tracking with S3 artifact store (extends CI/CD PRD milestones M1–M4).
7. Implement **sell-watch with QV-adapted triggers**; surface signals in the dashboard and curated parquet (email deferred to 2b).

### Phase 2b (validation + operations)

1. Historical **S&P 500 constituents including delisted** names (survivorship-bias mitigation).
2. **Full backtest** per `backtesting.md`: 20+ years, walk-forward 3–5 year windows, block-bootstrap Monte Carlo, crisis drawdown report, Sharpe gate vs four benchmarks.
3. **Cloud phase 2b**: Prefect or EventBridge orchestration, AWS SES email alerts, Streamlit dashboard hosted on AWS.

Magic Formula remains the strategy's **benchmark comparator** for Sharpe pass/fail in 2b; production portfolio construction follows the QV funnel throughout.

## User Stories

### Strategy and scoring

1. As an investor, I want the production pipeline to implement the Quantitative Value funnel (forensics → value → quality → portfolio), so that my model portfolio reflects the book's methodology rather than a Greenblatt placeholder.
2. As an investor, I want forensic accounting screens to hard-exclude companies at elevated fraud or bankruptcy risk before any value or quality score, so that permanent capital loss is filtered systematically.
3. As an investor, I want the Beneish M-Score included in forensic screening, so that earnings manipulation risk is part of the safety layer.
4. As an investor, I want companies in the bottom 5% of forensic models excluded (QVAL-style), so that the safety screen matches the published ETF process.
5. As an investor, I want the value screen to keep the top decile (~10%) of names by EBIT/TEV among survivors, so that I only quality-rank genuinely cheap stocks.
6. As an investor, I want quality ranked by the 10-point FS-Score (Gray/Carlisle variant) on the value pool, so that the final portfolio favors financially strong cheap names.
7. As an investor, I want the model portfolio to hold approximately 50 equal-weight long-only names after the quality screen, so that the portfolio matches QVAL concentration.
8. As an investor, I want every funnel stage to log how many names passed or failed, so that I can audit shrinkage from universe to portfolio.
9. As an investor, I want each score and exclusion to record formula version and inputs, so that any decision is reconstructible from the data lake.
10. As an investor, I want the dashboard to explain why a name is in the portfolio using QV stage outputs (forensic pass, EBIT/TEV rank, FS-Score components), so that the system stays explainable.
11. As a developer, I want Magic Formula ROC and EY scoring preserved as a separate benchmark path, so that backtests can compare QV against the Greenblatt replica without dual production logic.
12. As a developer, I want production and benchmark code paths named distinctly (QV vs MF), so that glossary terms in CONTEXT.md do not drift in implementation.

### Data and point-in-time

13. As a developer, I want annual and quarterly income, balance sheet, and cash flow stored in raw and curated zones, so that FS-Score year-over-year deltas are computable.
14. As a developer, I want the PIT fundamentals interface to return the correct historical filing rows for any decision date, so that backtests never leak future fundamentals.
15. As a developer, I want daily adjusted prices for at least a 5–10 year window in curated storage, so that light backtests and enterprise value history are supported.
16. As a developer, I want SimFin `shareprices/daily` as the primary price history source with a vendor fallback when needed, so that backtests are not blocked by free-tier snapshot lag.
17. As a developer, I want missing inputs for forensic or FS-Score rules routed to the review queue rather than silently dropped, so that data quality issues are visible.
18. As a developer, I want restatements to create new `version_id` rows with updated `as_of_date`, so that historical queries reflect what was knowable at each decision date.
19. As an investor, I want sector hard exclusions (banks, insurers, utilities) to remain upstream of QV scoring, so that incomparable financials never enter the funnel.

### Permanent loss and forensics

20. As an investor, I want Altman Z-score, interest coverage, net debt/EBITDA, negative equity, and delisting rules to remain available as distress signals, so that the permanent loss filter matches the existing spec where data allows.
21. As a developer, I want a CI regression test that forces Enron, Lehman, and WorldCom to be excluded at documented distress dates, so that bankruptcy screening cannot regress silently.
22. As a developer, I want each exclusion to store `rule_id`, `rule_version`, triggered values, and `as_of_date`, so that MLflow and the dashboard can show why a company was removed.
23. As a developer, I want fraud rules (restatement, auditor change, late filer) implemented where EDGAR data exists, with `unavailable` logged otherwise, so that the module is extensible without blocking on SEC ETL.

### Backtesting

24. As an investor, I want a light backtest over 5–10 years with annual rebalancing, so that I can see whether the QV strategy had acceptable risk-adjusted returns before investing further effort.
25. As an investor, I want the light backtest to recompute the full QV funnel at each rebalance date using only point-in-time data, so that results are not inflated by look-ahead bias.
26. As an investor, I want light backtest results compared to S&P 500 cap-weighted and Magic Formula replica benchmarks, so that I have familiar reference points.
27. As an investor, I want the light backtest universe limitation (current SimFin US, survivorship bias) clearly labeled in reports, so that I do not over-interpret early results.
28. As a developer, I want backtest runs logged as MLflow experiments with equity curve and trade ledger artifacts, so that each historical run is reproducible.
29. As a developer, I want long backtests to run outside PR CI (manual trigger or ECS ad-hoc task), so that commits are not blocked by 20-year simulations.
30. As an investor, I want Phase 2b to add a 20+ year walk-forward backtest with Monte Carlo and crisis drawdown reporting, so that the strategy meets the architecture validation bar.
31. As an investor, I want Phase 2b Sharpe compared against S&P 500 CW, S&P 500 EW, Russell 3000, and Magic Formula replica, so that pass/fail is objective when paper trading arrives later.
32. As a developer, I want delisted and bankrupt holdings handled with zero terminal price on delisting date in full backtests, so that NAV reflects realized losses.

### Cloud and MLOps

33. As a developer, I want the pipeline to run daily on ECS Fargate Spot without my laptop, so that the system is a real operational batch job.
34. As a developer, I want the data lake canonical store on S3 with a configurable lake root URI, so that the same code runs locally and in AWS.
35. As a developer, I want runtime secrets (e.g. `SIMFIN_API_KEY`) from AWS Secrets Manager, so that keys are not in the image or repository.
36. As a developer, I want MLflow run artifacts stored in S3, so that pipeline and backtest snapshots survive beyond a single machine.
37. As a developer, I want GitHub OIDC to deploy the pipeline image to ECR and update ECS task definitions on merge to `develop`, so that cloud deploys trace to git SHA.
38. As a developer, I want CloudWatch Logs for ECS task output, so that pipeline failures are debuggable.
39. As a portfolio reviewer, I want the README to document that Phase 2a cloud scope is pipeline-only (dashboard local), so that the MLOps story is honest about what runs where.
40. As a developer, I want Phase 2b to add SES email on sell-watch signals and host Streamlit on AWS, so that alerts and reporting work when I am not watching the dashboard.

### Sell-watch

41. As an investor, I want daily evaluation of model portfolio holdings for QV thesis breaks, so that I know when to consider exiting a position.
42. As an investor, I want a sell signal when forensic screening starts failing on a holding, so that fraud or distress triggers an alert.
43. As an investor, I want a sell signal when FS-Score drops materially (YoY or below threshold), so that quality deterioration is caught.
44. As an investor, I want a sell signal when a holding falls out of the EBIT/TEV value decile, so that overvaluation relative to the strategy is flagged.
45. As an investor, I want a sell signal when a watchlist name outranks a holding by a configurable margin on the QV composite rank, so that opportunity cost is monitored.
46. As an investor, I want sell signals to require manual confirmation before any future order build, so that the system never auto-sells.
47. As a developer, I want every holding evaluation logged (signal or no signal) for audit, so that false positive and false negative rates can be reviewed later.
48. As an investor, I want Phase 2b email alerts via AWS SES for new sell signals, so that I am notified without opening the dashboard.

### Documentation and governance

49. As a developer, I want a new feature spec `quantitative-value.md` as the canonical QV module before implementation, so that spec-driven workflow is preserved.
50. As a developer, I want CONTEXT.md updated when QV terms (quality, cheap, funnel rank) are resolved, so that agents and humans share one vocabulary.
51. As a developer, I want `roadmap.md` "After the demo" ordering updated to reflect QV-first production, so that docs do not contradict this PRD.

## Implementation Decisions

### Phasing

| Increment | Scope | Exit criterion |
| --- | --- | --- |
| **2a** | Multi-period data, forensics + Beneish, QV funnel, light backtest, cloud pipeline (S3 + ECS + MLflow S3), sell-watch logic + dashboard | Daily QV portfolio on ECS; light backtest equity curve in MLflow; sell signals in dashboard |
| **2b** | S&P 500 historical universe, full backtest spec, Prefect/EventBridge, SES, Streamlit on AWS | 20y walk-forward backtest with Sharpe gate; email alerts; dashboard on AWS |

Paper trading and broker execution are explicitly **out of Phase 2** (deferred until a passing full backtest exists in a later phase).

### Deep modules (build or extend)

These are intentionally **deep modules**: narrow public interfaces, substantial internal logic, stable contracts, testable in isolation.

#### 1. Point-in-time fundamentals store (extend)

- **Responsibility:** Given `decision_date` and `ticker` (or universe), return the latest fundamental rows per statement type with `as_of_date <= decision_date`; support multiple historical periods for YoY deltas.
- **Interface shape:** Query functions returning normalized provider-agnostic columns (`ebit`, `total_assets`, `cash`, etc.) plus metadata (`as_of_date`, `version_id`, `formula_version`).
- **Consumers:** Forensic evaluator, FS-Score calculator, EV/EBIT/TEV metrics, backtest engine.
- **Change frequency:** Low — extended for multi-period, not replaced.

#### 2. Forensic evaluator (new)

- **Responsibility:** Evaluate all fraud and distress rules per company at a run date; compute Beneish M-Score; compute cross-sectional percentiles; apply QVAL bottom-5% exclusion per model; emit hard `exclude` or `pass` with reasons.
- **Interface shape:** Input: universe pass list + PIT fundamentals (+ optional filing flags). Output: exclusions table keyed by `(cik, run_date)` with `rule_id`, `triggered_value`, `threshold`, `explanation`.
- **Consumers:** QV funnel stage 1, sell-watch `SW_FORENSIC`, CI regression fixtures.
- **Change frequency:** Medium — thresholds tuned, new rules versioned.

#### 3. FS-Score calculator (new)

- **Responsibility:** Compute the 10 binary FS-Score components (Gray/Carlisle variant: profitability, stability, recent operational improvements) from multi-period PIT inputs; sum to integer score 0–10.
- **Interface shape:** Input: PIT income/balance/cashflow history for one ticker at `decision_date`. Output: component dict, total score, `formula_version`.
- **Consumers:** QV funnel stage 3, sell-watch `SW_FS_SCORE_DROP`, dashboard explainability.
- **Change frequency:** Low — tied to published FS-Score definition.

#### 4. QV funnel orchestrator (new)

- **Responsibility:** Run sequential funnel stages with auditable counts; no scoring logic inside — delegates to forensic evaluator, value ranker, FS-Score ranker, portfolio constructor.
- **Stages:**
  1. Universe pass (from universe construction)
  2. Forensic hard exclusion
  3. Value screen: rank by EBIT/TEV descending; keep top decile (configurable count or fraction)
  4. Quality screen: FS-Score on value pool; keep top 50 (configurable)
  5. Portfolio: equal-weight selected names; optional market-cap tie-break on rank ties
- **Interface shape:** Input: `run_date`, lake root, config. Output: `ScoringResult`-like object with stage counts, ranked tables per stage, final `model_portfolio` rows, MLflow-ready metrics.
- **Consumers:** `score-universe` CLI, dashboard, backtest engine, sell-watch.
- **Change frequency:** Low — stage order fixed by QV methodology.

#### 5. Value metrics (extend from cheapness module)

- **Responsibility:** Compute EBIT, enterprise value, EBIT/TEV (same EV definition as Earnings Yield module); cross-sectional rank within forensic survivors.
- **Interface shape:** Reuse existing metrics building blocks where possible; separate production path from MF `EY rank`.
- **Consumers:** QV funnel stage 2, sell-watch `SW_VALUE_POOL_EXIT`.

#### 6. Magic Formula benchmark path (preserve, demote)

- **Responsibility:** ROC + EY + combined rank + top-N portfolio exactly as demo slice; used only for benchmark portfolio reconstruction in backtests.
- **Interface shape:** Existing ranking module interface unchanged; invoked only from backtest benchmark builder and smoke tests until smoke test updated to QV path.
- **Consumers:** Backtest benchmark comparator, CI smoke test (transition: add QV smoke, keep MF benchmark test).

#### 7. Light backtest engine (new)

- **Responsibility:** Loop rebalance dates; pin PIT data per date; invoke full QV funnel; simulate equal-weight holdings and daily NAV from curated prices; compare to benchmark series.
- **Interface shape:** Input: `start_date`, `end_date`, `rebalance_frequency`, config hash. Output: equity curves, trade ledger, holdings parquet, summary metrics → MLflow `backtesting` experiment.
- **Constraints:** No live network in run; read only curated parquet; custom loop (ADR-0002: no Zipline).
- **Consumers:** Manual/ECS ad-hoc runs, dashboard backtest panel (Phase 2a minimal).

#### 8. Sell-watch evaluator (new)

- **Responsibility:** For each model portfolio holding at `run_date`, evaluate QV triggers; dedupe against confirmed/dismissed history; write signals and full evaluation audit.
- **Trigger IDs:** `SW_FORENSIC`, `SW_FS_SCORE_DROP`, `SW_VALUE_POOL_EXIT`, `SW_QV_OPPORTUNITY` (replace ROC/EY triggers from sell-watch spec for production).
- **Interface shape:** Input: holdings, watchlist, latest scores, config thresholds. Output: signals parquet + evaluations parquet.
- **Consumers:** Dashboard, SES (2b), future broker module.

#### 9. Lake root and cloud runtime (extend)

- **Responsibility:** Abstract storage backend (local file vs S3 prefix); same zone layout (raw, curated, issues); DuckDB reads parquet from configured root.
- **Interface shape:** Single `LAKE_ROOT_URI` (or equivalent) consumed by all ingest and scoring CLIs.
- **Consumers:** All pipeline stages, ECS task entrypoint, ingest-smoke workflow.
- **Aligns with:** CI/CD PRD milestones M1–M4 for 2a; M4 uses EventBridge cron → ECS Fargate Spot → pipeline entrypoint.

### Production vs benchmark separation

| Concern | Production (Phase 2+) | Benchmark only |
| --- | --- | --- |
| Safety | Forensic evaluator + permanent loss rules | — |
| Value | EBIT/TEV value decile | EY rank (MF) |
| Quality | FS-Score on value pool | ROC rank (MF) |
| Ranking | QV funnel sequential rank | Combined rank = ROC + EY |
| Portfolio size | ~50 EW default | MF replica uses same universe/filters as configured for comparison |

### Configuration and versioning

- QV funnel parameters (decile fraction, portfolio size, FS-Score tie-break) live in versioned YAML under a `config/quantitative_value/` namespace.
- Forensic thresholds and Beneish coefficients versioned under `config/permanent_loss/`.
- Sell-watch thresholds versioned under `config/sell_watch/` with QV trigger IDs.
- Every MLflow run logs `git_sha`, config hashes, and stage counts.

### Dashboard changes

- Replace ROC/EY-centric explainability with QV stage breakdown per ticker.
- Add light backtest summary panel (equity curve, key metrics, survivorship bias warning).
- Add sell-watch signal list with trigger detail and confirm/dismiss actions (confirm does not build orders in Phase 2).

### Glossary updates (CONTEXT.md)

When implementation starts, resolve:

- **Quality (production):** FS-Score composite, not ROC alone.
- **Cheap (production):** Membership in EBIT/TEV value pool, not EY rank alone.
- **QV funnel rank:** Order after quality screen within the value pool; supersedes **combined rank** for production.
- **Combined rank:** Retained for **Magic Formula replica** benchmark only.

### Dependency order (2a)

1. Feature spec `quantitative-value.md`
2. Multi-period ETL + PIT extension + daily prices
3. Forensic evaluator (+ Beneish)
4. FS-Score calculator
5. QV funnel orchestrator wired into scoring CLI
6. Light backtest engine
7. Cloud 2a (pipeline stable locally first)
8. Sell-watch evaluator + dashboard

## Testing Decisions

### Principles

- Test **external behavior** (inputs → outputs, exclusions, ranks, portfolio membership) not internal implementation details.
- All PR CI tests use **pinned fixtures** — no SimFin, yfinance, or AWS calls in the default test job.
- Fixture design must respect **point-in-time correctness** (no row with `as_of_date > decision_date` in historical scenarios).
- Long-running backtests and full 20-year walk-forward run **outside PR CI** (manual or scheduled ECS).

### Modules to test (priority)

| Module | Priority | What to assert |
| --- | --- | --- |
| Forensic evaluator | **P0** | Enron, Lehman, WorldCom excluded at fixture dates; Beneish bottom-5% gate; exclusion reason columns populated |
| FS-Score calculator | **P0** | Known fixture company gets expected 0–10 score; each binary component matches hand-checked inputs |
| QV funnel orchestrator | **P0** | Fixture universe shrinks monotonically through stages; final portfolio size ≤ configured cap; excluded names never appear |
| Value metrics (EBIT/TEV) | **P1** | EV formula matches versioned config; negative EBIT routed to review queue |
| PIT fundamentals store | **P1** | Historical `decision_date` returns correct row; restatement version selection |
| Light backtest engine | **P1** | No look-ahead: fundamentals after rebalance date absent; turnover ledger balances |
| Sell-watch evaluator | **P1** | Each trigger fires on constructed holding; no signal when thresholds not met; dedupe of confirmed signals |
| Magic Formula benchmark | **P1** | Regression: demo slice ROC/EY/combined rank unchanged on fixtures (benchmark path not broken) |
| Lake root abstraction | **P2** | Local vs `s3://` prefix resolves same relative paths (mock or minio optional) |

### Prior art in codebase

- `fixture_lake.py` and `point_in_time_fundamentals()` for PIT fixture queries.
- `magic_formula_ranking.py` tests (if present) for rank assignment and portfolio selection patterns.
- CI/CD PRD user story 7: smoke test on fixture vertical slice — **update smoke to QV funnel** once forensic + funnel exist; keep MF benchmark unit tests separate.
- Permanent loss spec: Enron / Lehman / WorldCom regression cases under `tests/fixtures/permanent_loss/`.

### CI vs integration

| Tier | Runs | Scope |
| --- | --- | --- |
| PR CI | Every pull request | Lint, unit tests, QV smoke on fixtures, forensic regression |
| Ingest-smoke | Weekly / manual | S3 write from SimFin (existing CI/CD PRD workflow) |
| Light backtest | Manual / ECS ad-hoc | Real curated lake, 5–10 years |
| Full backtest (2b) | Manual / ECS / Batch | 20+ years, walk-forward, Monte Carlo |

## Out of Scope

- **Paper trading and broker execution** — no simulated or real orders in Phase 2.
- **Auto-execution of sell signals** — confirm/dismiss only; no order builder.
- **Corroborative signals** (buybacks, insider, short interest) — deferred.
- **Unstructured financial data** (LLM filings, going-concern NLP) — deferred; `BK_GOING_CONCERN` remains future.
- **SEC EDGAR normalizer as primary fundamentals source** — optional 2b+; SimFin remains primary for Phase 2.
- **Moat "pre-flight checklist"** and full forensic model zoo beyond Beneish + spec distress rules — optional 2b+.
- **Score-weighted and risk-parity portfolio weighting** — equal-weight only in 2a; weighting as backtest hyperparameter in 2b only.
- **Personal portfolio CSV evolution and NAV** — `portfolio-evolution.md` deferred.
- **Prefect server, Streamlit on AWS, SES** — Phase 2b only (not 2a).
- **Production deploy to prod ECS on `main`** — may follow 2a dev deploy; prod CD per CI/CD PRD Phase 2 when ready.
- **Zipline or third-party backtest frameworks** — rejected (ADR-0002).

## Further Notes

### Time and risk

- **2a:** ~13–16 weeks at 10–15 h/week if SimFin data coverage is sufficient.
- **2b:** ~8–12 additional weeks.
- **Risks:** SimFin free-tier limits on multi-period and daily prices; survivorship bias in 2a light backtest (must be labeled); Beneish missing inputs shrinking the funnel; backtest compute cost (full funnel × rebalance dates) — plan DuckDB pushdown or materialized stage tables early.

### Open question (not blocking PRD)

- **Portfolio size:** QVAL uses ~50 names; demo uses 30. Default recommendation: **50** with configurable cap in QV config. Resolve in `quantitative-value.md` spec before coding.

### Relationship to other documents

- This PRD does **not** replace per-module feature specs; it coordinates them. Each module keeps acceptance criteria in `spec/features/`.
- Implementers should read ADR-0001 (SimFin fundamentals), ADR-0002 (demo scope cut / no Zipline), and the CI/CD PRD before cloud work.
- After Phase 2a ships, update `roadmap.md` "After the demo" ordering and `mission.md` functional flow to state QV as production scoring.

### Suggested GitHub issue title

`PRD: MVP Phase 2 — Quantitative Value, Cloud, Backtest, Sell-Watch`

Link this PRD path in the issue body; label `ready-for-agent` when creating tracker entry.
