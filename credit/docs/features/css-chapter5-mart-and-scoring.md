# Feature: CSS Chapter 5 — Application mart and scratch scoring

**Status:** in progress — book path + competition raw (#151) + competition mart (#152) + AMEX categoricals ([#157](https://github.com/JLaborda/SmartWealthAI/issues/157)) done; **scratch scoring + thin MLOps (#145 / #161)** done on develop; **FastAPI serving** (score + risk drivers, same `pipeline.joblib`) active this cut; local PSI + Terraform stretch are separate week slices; competition EDA (#153) remains parallel  
**GitHub:** parent [#142](https://github.com/JLaborda/SmartWealthAI/issues/142) · done: [#143](https://github.com/JLaborda/SmartWealthAI/issues/143) → [#144](https://github.com/JLaborda/SmartWealthAI/issues/144) → [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) → [#151](https://github.com/JLaborda/SmartWealthAI/issues/151) → [#152](https://github.com/JLaborda/SmartWealthAI/issues/152) · [#157](https://github.com/JLaborda/SmartWealthAI/issues/157) · [#145](https://github.com/JLaborda/SmartWealthAI/issues/145)/[#161](https://github.com/JLaborda/SmartWealthAI/pull/161) · **active:** FastAPI serving (Friday demo week) · parallel: [#153](https://github.com/JLaborda/SmartWealthAI/issues/153), PSI CLI, [#162](https://github.com/JLaborda/SmartWealthAI/pull/162) glossary  
**Code:** `credit/src/credit/application_mart.py`, `credit/src/credit/competition_mart.py`, `credit/src/credit/scoring_pipeline.py`, `credit/src/credit/api.py`, `credit/src/credit/binning.py`, `credit/src/credit/model.py`, `credit/src/credit/cli.py` · Notebook: `credit/notebooks/eda_application_mart.ipynb` (book-sample smoke; optional only) · Tests: `tests/credit/test_application_mart.py`, `tests/credit/test_competition_mart.py`, `tests/credit/test_scoring_pipeline.py`, `tests/credit/test_api_serving.py` · Sample: `credit/data/train_df_sample.pkl` (Git LFS) · Artifact: `pipeline.joblib` · Images: `credit/Dockerfile` (batch score), `credit/Dockerfile.serve` (FastAPI)  
**Domain:** credit / CSS (Credit Scoring System)  
**Glossary:** [`../../CONTEXT.md`](../../CONTEXT.md) · Map: [`../../../CONTEXT-MAP.md`](../../../CONTEXT-MAP.md)  
**Book:** *Financial AI in Practice* chapters 5–6 (chapter 5 only in this spec)

## Problem Statement

The portfolio needs a demonstrable **application credit scoring** slice with real ML (not only an equity screener). Without a coded CSS path, interviewers cannot see end-to-end finance ML: demo data → **application mart** → model → **credit score** → rank by default risk.

## Solution

Deliver chapter 5 of the book as a real `credit` Poetry package and CLIs (local, no Airflow/AWS yet):

1. Register the `credit` package in the monorepo Poetry project.
2. Build a validated **application mart** from public demo data: book sample (smoke/hermetic) plus official **AMEX** and **Home Credit** **raw competition extracts** (local Kaggle CLI; FICO HELOC later).
3. Train a scratch pipeline (WOE/IV → XGBoost → probability → **credit score** with book scaling) and report **AUC** + **KS** on holdout; **rank-only** (no approve/decline cutoff). Serious training targets competition-backed marts; fixtures/book remain CI/smoke.

## User Stories

1. As a hiring manager, I want a top-level `credit/` domain with a runnable CSS path, so that the portfolio shows credit risk work at a glance.
2. As a developer, I want a single `poetry install` to include the `credit` package, so that I do not maintain a second environment.
3. As a developer, I want a credit CLI entry point, so that I can discover and run CSS stages like investing CLIs.
4. As a credit analyst, I want an **application mart** with one row per application, so that modeling uses a stable table.
5. As a credit analyst, I want the mart README to document which column is the **target** and which value means **bad**, so that default semantics are honest for public demo data.
6. As a developer, I want hermetic fixture-based tests for mart build, so that CI does not need Kaggle/network.
7. As a developer, I want invalid or unusable rows routed to an explicit reject/issue count, so that bad data is not silently scored.
8. As a data scientist, I want develop vs holdout split (time-based when a decision date exists, else stratified random with a documented limitation), so that WOE and model fit do not leak into holdout.
9. As a data scientist, I want manual WOE/IV on the develop set, so that chapter 5 scratch methodology is reproduced.
10. As a data scientist, I want an XGBoost classifier on WOE features, so that default probability is estimated.
11. As a credit analyst, I want probability converted to a **credit score** using book pdo/base parameters, so that ranking uses score points, not raw PD only.
12. As a credit analyst, I want applications ranked by credit score (risk order), so that the demo shows scoring without an assignment engine.
13. As a risk stakeholder, I want holdout **AUC-ROC** and **KS** printed by the CLI, so that discrimination quality is visible.
14. As a developer, I want chapter 6 OptBinning/Evidently/SHAP deferred, so that chapter 5 lands as two focused PRs.
15. As a portfolio owner, I want no Airflow or Terraform in this slice, so that local domain work finishes before `platform/`.
16. As an interviewer, I want clear disclaimers that demo data is public (not live bank BFSI), so that the story stays credible.
17. As a developer, I want investing lake/SimFin code untouched by credit imports, so that bounded contexts stay separate.
18. As a future maintainer, I want stage names that match the book’s pipeline mental model, so that cloud orchestration can wrap the same stages later.
19. As a data scientist, I want a short EDA notebook on the **application mart** after PR1, so that I can explore class balance and data quality before modeling without duplicating the book’s notebook-only delivery.
20. As a data scientist, I want official Kaggle **raw competition extracts** (AMEX + Home Credit) hosted locally via Kaggle CLI, so that EDA and modeling can improve beyond the book sample.
21. As a developer, I want AMEX converted locally to parquet from the official extract (not community mirrors as source of truth), so that working size is manageable with controlled provenance.
22. As a data scientist, I want competition-backed marts and EDA before scratch scoring, so that #145 is informed by real contest data rather than copy-paste of the book alone.
23. As a developer, I want a local FastAPI service that loads `pipeline.joblib` and exposes `POST /score` then `POST /drivers`, so that the Friday demo can curl PD / credit score / rank and top-k risk drivers without a batch parquet round-trip.
24. As a developer, I want hermetic API tests with example feature JSON from the scoring fixture mart, so that CI never needs gitignored `data/credit/` marts or a network.

## Implementation Decisions

- **Packaging:** One Poetry project; add `credit` as a second package beside investing; credit CLIs via project scripts.
- **Primary test seam (PR1):** a single `build_application_mart(...)` (or equivalent) function that takes a local source path and returns a result with mart rows written, target→bad/good mapping metadata, and retained/rejected counts. CLI is a thin wrapper.
- **Demo data:** book sample (LFS) = smoke/hermetic + notebook fidelity; **priority path** = official AMEX + Home Credit raw extracts under `data/credit/raw/{amex,home_credit}/` (gitignored); local AMEX CSV→parquet conversion under our control; **FICO HELOC later** (documented only). Never imply live BFSI. No Kaggle leaderboard submissions in this slice. No S3/DVC in MVP.
- **Raw layout language:** operator docs may say “local raw”; domain speech is **raw competition extract** → **application mart** (do not copy the investing lake vocabulary into credit).
- **Split:** time-based when application/decision date exists; else stratified random; document on mart README; fit WOE/model on develop only. **Closed (competition AMEX):** that mart is **static competition data** (not point-in-time / as-of dated); use stratified random only — do not add dating for this path.
- **Label language:** provider **target** column in schemas; domain speech **bad**/**good**.
- **Score use (v1):** rank-only; no cutoff; book probability→score scaling first.
- **Metrics (PR2 CLI):** AUC-ROC + KS on holdout (Gini optional later).
- **Orchestration:** CLI + composable stages; not Airflow locally.
- **EDA:** Book-sample notebook = smoke (#147 done). Competition-mart EDA (#153) is a **generalist** pass (class balance, missingness, dtypes/cats present, target definition check, obvious DQ / leakage smells) plus a short **“possible later data improvements”** notes section — **not** a feature-engineering project and **not** a hard gate on scratch scoring (#145). Prefer starting #145 on the book-sample path in parallel; competition-backed scoring can follow after #153 has flagged or cleared serious data issues. EDA may *propose* mart/schema improvements; implementing them needs the schema-change communication bar (issue + spec + READMEs).
- **AMEX statement → application grain (#157 done):** continuous numerics → `mean`/`std`/`min`/`max`/`last`; official categoricals (`B_30`, `B_38`, `D_114`, `D_116`, `D_117`, `D_120`, `D_126`, `D_63`, `D_64`, `D_66`, `D_68`) → **`mode` + `last` only**; non-numeric statement features are not silently dropped (`{col}_mode` / `{col}_last`).
- **No extra feature engineering in this cut (owner decision):** keep the book/AMEX-style aggregation contract above. No rolling windows, EWMA, short-horizon stats, or other FE beyond what the prepare already ships. Recency is represented by `*_last` only until a later, explicit schema-change slice.
- **Feature selection (locked, book-aligned):**
  - Drop columns with null fraction ≥ **80%** (`NULL_DROP_THRESHOLD = 0.80`).
  - Fit WOE/IV on remaining develop features; **keep IV ≥ 0.02** (`IV_THRESHOLD`, book `iv_threshold=0.02`).
  - No fixed 8-feature shortlist; no forced drop of the weaker of `P_2_last` / `D_48_last`.
- **WOE numeric bins (locked):** `WoeBinner.n_bins = 10`, matching book chapter 5 `pd.qcut(..., 10, duplicates='drop')`.
- **Artifact contract (#145):** `credit-css fit` writes a single **`pipeline.joblib`** containing WOE/IV binner + XGBoost classifier + score-scaling params. `credit-css score` (and `credit/Dockerfile` batch entrypoint) loads that file → **PD** + book-scaled **credit score** + **rank**. MLflow on fit logs params, develop/holdout AUC+KS, and the joblib (file store / `$MLFLOW_TRACKING_URI` OK).
- **FastAPI serving (Friday demo week, locked):** lives under `credit/` (not `platform/`). Loads the **same** `pipeline.joblib` via env `CREDIT_PIPELINE_ARTIFACT` (or `create_app(artifact_path=...)`). Two POSTs:
  1. **`POST /score`** — body = feature JSON (`application_id` + `features` map). Response: `pd`, `credit_score`, `rank` (single-application requests return `rank=1`; rank-only, no cutoff).
  2. **`POST /drivers`** — same feature JSON + optional `top_k` (default 5). Response: top-k **risk drivers** ranked by **gain × |WOE|** for that row (XGBoost gain × absolute WOE of the applicant’s bin). **SHAP** on drivers = stretch / later.
  Example payloads come from the hermetic scoring fixture mart (`tests/credit/fixtures/scoring_mart/`), never from gitignored `data/credit/` marts. Serving image: `credit/Dockerfile.serve` (uvicorn). Terraform / AWS = out of this slice.
- **Score scaling params (locked):** book chapter 5 numbers (PDO=20, base_score=650, base_odds=20) with **PDO polarity** — odds = `(1−PD)/PD` (good:bad); +20 points ≈ doubles good-borrower odds; clip `[250, 1000]`. Higher `credit_score` = safer; rank 1 = highest score. (Notebook cell that used `PD/(1−PD)` inverted this; we follow the book PDO prose.) Tagged `scaling_source=book_chapter5_pdo_good_odds`.
- **Mart schema change communication (owner decision):** green tests are not enough. For every credit stage that creates, drops, or renames mart columns / changes grain (raw → application), the change must (1) say so in the PR/agent summary in plain language, (2) update the mart README sidecar and `credit/data/README.md` in the same change, and (3) open or update a GitHub issue plus a line in this feature spec **before** merge. Example that failed this bar once: silent loss of AMEX categoricals before [#157](https://github.com/JLaborda/SmartWealthAI/issues/157).
- **Delivery:** scaffold (#143) → mart (#144) → book EDA (#147) → competition raw (#151) → competition mart (#152) → fix AMEX cats (#157) → scratch scoring + thin MLOps (#145/#161) → **FastAPI serving (this cut)** → local PSI (next) → Terraform stretch → competition-backed retrains if needed.

## Testing Decisions

- Test **external behavior** of the highest seam only where possible (ideal: one seam for PR1 = `build_application_mart`).
- Hermetic fixtures under the credit test tree; no network in unit/CI tests.
- Prior art: investing SimFin normalizer tests (`normalize_simfin` result + written parquet assertions) — mirror that style for the mart.
- PR2: assert CLI or pure function returns AUC/KS and produces ranked scores on a tiny fixture; do not assert internal WOE bin edges unless they are part of a documented public contract.
- FastAPI serving: hermetic `TestClient` tests against an app built with a fixture-fitted `pipeline.joblib`; assert `/score` returns `pd` / `credit_score` / `rank` and `/drivers` returns ordered top-k feature names with gain×|WOE| scores. Example request bodies are derived from `tests/credit/fixtures/scoring_mart/` rows.

## Out of Scope

- Chapter 6 OptBinning scorecard; Evidently; **SHAP/LIME** on the drivers endpoint (stretch)
- Local **PSI** data-drift CLI (next Friday-demo slice — not this FastAPI PR)
- Approve/decline cutoff or profit/risk optimization
- Agent–client assignment / matching
- Airflow, AWS, Terraform / `credit/infra/`, `platform/` / S3-backed credit raw store (local + Kaggle CLI for MVP; Terraform = stretch later)
- Kubernetes / compose swarm for credit scoring
- Kaggle leaderboard submissions
- Community redistributed AMEX parquet/feather as primary provenance
- Extra FE beyond the book/AMEX aggregation contract (rolling windows, EWMA, short-horizon stats, etc.)
- Feature store (Feast / Tecton / similar), DVC, and credit **model-registry / model-change demo** slices beyond thin MLflow fit logging (explicit later backlog — not chapter 5)
- Fraud module
- Migrating investing code into `investing/`
- Poetry → uv migration
- Closing or implementing Phase 2 QV (cancelled; `archive/phase2-qv`)
- Notebook as source of truth for scoring (optional notebook may call the library only)
- Changing WOE/IV/XGB defaults solely for serving (serving loads the existing artifact API)

## Further Notes

- Expand “CSS” on first README mention: Credit Scoring System.
- Parent GitHub issue [#142](https://github.com/JLaborda/SmartWealthAI/issues/142) tracks this spec; child tickets are tracer bullets for agents. Competition wave: [#151](https://github.com/JLaborda/SmartWealthAI/issues/151) → [#152](https://github.com/JLaborda/SmartWealthAI/issues/152) → [#157](https://github.com/JLaborda/SmartWealthAI/issues/157) → [#153](https://github.com/JLaborda/SmartWealthAI/issues/153) → [#145](https://github.com/JLaborda/SmartWealthAI/issues/145).
- **Later (not this cut):** document a credit model change with experiment/model registry (likely reuse investing’s MLflow pattern — registry ≠ feature store). DVC only if we need versioned large datasets beyond gitignore + LFS + local raw; MVP already says no DVC.
