# Context Map

SmartWealthAI is a **portfolio monorepo**: several financial domains in one repo so interviewers (including managers) can see end-to-end finance engineering at a glance. Domains share platform patterns only when useful; they do **not** share domain language.

## Repo shape (domain-first)

Top-level folders are **products/domains**, not technical layers:

| Path | Domain |
| --- | --- |
| `investing/` | Value investing / Magic Formula — code, specs, dashboard, and tests live here (`investing/src/investing/`, `investing/docs/`, `investing/apps/dashboard/`, `investing/tests/`) |
| `credit/` | Credit scoring / scorecard — **active**; code and specs under `credit/` (`credit/docs/`, `credit/tests/`) |
| `fraud/` | Fraud detection (future — create when that module starts) |
| `platform/` | Shared infra (Terraform, AWS, shared API) — **only after** domain demos work locally |

**Packaging:** root uv workspace (`uv sync`); members `credit` + `investing` with PEP 621 scripts under `credit/src` and `investing/src` ([ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md), #182). Lean per-domain deps: #183.

Do **not** put shared `ingest/`, `benchmarks/`, or `serving/` at the repo root as peers of domains.

## Contexts

- [Equity screening / investing](./investing/CONTEXT.md) — quantitative value / Magic Formula on US equities.
- [Credit risk — CSS](./credit/CONTEXT.md) — application credit scoring / scorecard (Elliot Taehun Kim, *Financial AI in Practice*, chapters 5–6).
- Fraud — not started.

## Relationships

- **Investing ↔ Credit ↔ Fraud**: no domain coupling. Shared only via `platform/` (later) and repo tooling/CI.
- Do not reuse investing terms (ROC, EY, model portfolio) for credit, or credit terms (scorecard, WOE, PSI) for investing.
- **Phase 2 Quantitative Value** (forensics, FS-Score, backtest, sell-watch as production scoring): **cancelled for active execution** ([ADR-0003](docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`). Demo-slice investing stays as delivered.
- **Cloud / `platform/`**: deferred until credit (and other) domain content is demonstrable locally; then generalized (not a daily QV job).

## Delivery sequencing (credit)

Feature specs land under [`credit/docs/`](credit/docs/) (index: [`credit/docs/README.md`](credit/docs/README.md)). Investing specs live under [`investing/docs/`](investing/docs/).

1. **Book content first** (local), chapter order: ch.5 scratch → ch.6 OptBinning/monitoring/explainability.
2. **Chapter 5 delivery:** target **C** in **two PRs** — **PR1 = mart** (load/clean/validate); **PR2 = WOE/IV + XGBoost + probability → credit score (**book scaling params**; refine later) + CLI (**AUC + KS**); **rank-only** (cutoff/profit trade-off later)**. Chapter 6 is a later cut. Train/holdout: **time-based when a decision/application date exists, else stratified random** (document the limitation); fit WOE/model on develop only.
3. **Demo data**: book sample (`train_df_sample.pkl` after LFS) for smoke / notebook fidelity. **Priority path:** official Kaggle **raw competition extracts** for **AMEX Default Prediction** and **Home Credit Default Risk** (local + Kaggle CLI; gitignored; AMEX converted locally to parquet under controlled rules — not community mirrors as source of truth). **FICO HELOC** later (Kaggle/HF mirrors or official FICO form). Access-only (no leaderboard submissions). Never imply live bank BFSI data.
4. **Local orchestration (credit v1):** CLI + composable stages (not Airflow in-process). Document stage names to match the book’s pipeline so `platform/` can wrap them later.
5. **`platform/` later**: Terraform / AWS / shared serving after the domain slice works. **Airflow vs EventBridge/ECS vs Prefect** stays open until that phase.

## Portfolio intent

Each domain folder should be understandable from its own `README.md`. The root README is a one-screen map of domains, not a blended “AI finance app.”

## Sources

1. **Joel Greenblatt (2010)** — *The Little Book That Still Beats the Market*
   Foundations of the Magic Formula: systematic ranking by return on capital (ROC) and earnings yield.

2. **Wesley R. Gray & Tobias E. Carlisle (2012)** — *Quantitative Value: A Practitioner's Guide to Automating Intelligent Investment and Eliminating Behavioral Errors*
   Quantitative framework for accounting-manipulation screens (M-Score / F-Score), financial strength, competitive advantages (moats), and intrinsic valuation. **Not in active execution** in this repo (see [ADR-0003](docs/adr/0003-phase2-qv-cancelled.md)); kept as provenance for the cancelled Phase 2 QV path.

3. **Elliot Taehun Kim (2026)** — *Financial AI in Practice: A Playbook for Credit, Fraud, and Investment Systems*
   Architecture patterns, feature engineering, and ML pipelines for credit risk, fraud, and investment systems (credit CSS follows chapters 5–6).
