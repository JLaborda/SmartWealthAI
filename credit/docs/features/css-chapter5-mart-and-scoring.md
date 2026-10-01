# Feature: CSS Chapter 5 — Application mart and scratch scoring

**Status:** in progress — book path + competition raw (#151) + competition mart (#152) + AMEX categoricals ([#157](https://github.com/JLaborda/SmartWealthAI/issues/157)) done; **next:** competition EDA (#153) then scoring (#145)  
**GitHub:** parent [#142](https://github.com/JLaborda/SmartWealthAI/issues/142) · done: [#143](https://github.com/JLaborda/SmartWealthAI/issues/143) → [#144](https://github.com/JLaborda/SmartWealthAI/issues/144) → [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) → [#151](https://github.com/JLaborda/SmartWealthAI/issues/151) → [#152](https://github.com/JLaborda/SmartWealthAI/issues/152) · **now:** [#157](https://github.com/JLaborda/SmartWealthAI/issues/157) done (unblocks [#153](https://github.com/JLaborda/SmartWealthAI/issues/153)) → [#145](https://github.com/JLaborda/SmartWealthAI/issues/145)  
**Code:** `credit/src/credit/application_mart.py`, `credit/src/credit/competition_mart.py`, `credit/src/credit/cli.py` · Notebook: `credit/notebooks/eda_application_mart.ipynb` (book-sample smoke) · Tests: `tests/credit/test_application_mart.py`, `tests/credit/test_competition_mart.py` · Sample: `credit/data/train_df_sample.pkl` (Git LFS)  
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

## Implementation Decisions

- **Packaging:** One Poetry project; add `credit` as a second package beside investing; credit CLIs via project scripts.
- **Primary test seam (PR1):** a single `build_application_mart(...)` (or equivalent) function that takes a local source path and returns a result with mart rows written, target→bad/good mapping metadata, and retained/rejected counts. CLI is a thin wrapper.
- **Demo data:** book sample (LFS) = smoke/hermetic + notebook fidelity; **priority path** = official AMEX + Home Credit raw extracts under `data/credit/raw/{amex,home_credit}/` (gitignored); local AMEX CSV→parquet conversion under our control; **FICO HELOC later** (documented only). Never imply live BFSI. No Kaggle leaderboard submissions in this slice. No S3/DVC in MVP.
- **Raw layout language:** operator docs may say “local raw”; domain speech is **raw competition extract** → **application mart** (do not copy the investing lake vocabulary into credit).
- **Split:** time-based when application/decision date exists; else stratified random; document on mart README; fit WOE/model on develop only.
- **Label language:** provider **target** column in schemas; domain speech **bad**/**good**.
- **Score use (v1):** rank-only; no cutoff; book probability→score scaling first.
- **Metrics (PR2 CLI):** AUC-ROC + KS on holdout (Gini optional later).
- **Orchestration:** CLI + composable stages; not Airflow locally.
- **EDA:** Book-sample notebook = smoke (#147 done). Competition-mart EDA (#153) unblocked after AMEX mart keeps all official categoricals ([#157](https://github.com/JLaborda/SmartWealthAI/issues/157) done); run EDA before serious #145 work.
- **AMEX statement → application grain (#157 done):** continuous numerics → `mean`/`std`/`min`/`max`/`last`; official categoricals (`B_30`, `B_38`, `D_114`, `D_116`, `D_117`, `D_120`, `D_126`, `D_63`, `D_64`, `D_66`, `D_68`) → **`mode` + `last` only**; non-numeric statement features are not silently dropped (`{col}_mode` / `{col}_last`).
- **Delivery:** scaffold (#143) → mart (#144) → book EDA (#147) → **competition raw (#151) → competition mart (#152) → fix AMEX cats (#157) → competition EDA (#153) → scoring (#145)**.

## Testing Decisions

- Test **external behavior** of the highest seam only where possible (ideal: one seam for PR1 = `build_application_mart`).
- Hermetic fixtures under the credit test tree; no network in unit/CI tests.
- Prior art: investing SimFin normalizer tests (`normalize_simfin` result + written parquet assertions) — mirror that style for the mart.
- PR2: assert CLI or pure function returns AUC/KS and produces ranked scores on a tiny fixture; do not assert internal WOE bin edges unless they are part of a documented public contract.

## Out of Scope

- Chapter 6 (OptBinning scorecard, Evidently/PSI monitoring, SHAP/LIME)
- Approve/decline cutoff or profit/risk optimization
- Agent–client assignment / matching
- Airflow, AWS, Terraform, `platform/` / S3-backed credit raw store (local + Kaggle CLI for MVP)
- Kaggle leaderboard submissions
- Community redistributed AMEX parquet/feather as primary provenance
- Fraud module
- Migrating investing code into `investing/`
- Poetry → uv migration
- Closing or implementing Phase 2 QV (cancelled; `archive/phase2-qv`)

## Further Notes

- Expand “CSS” on first README mention: Credit Scoring System.
- Parent GitHub issue [#142](https://github.com/JLaborda/SmartWealthAI/issues/142) tracks this spec; child tickets are tracer bullets for agents. Competition wave: [#151](https://github.com/JLaborda/SmartWealthAI/issues/151) → [#152](https://github.com/JLaborda/SmartWealthAI/issues/152) → [#157](https://github.com/JLaborda/SmartWealthAI/issues/157) → [#153](https://github.com/JLaborda/SmartWealthAI/issues/153) → [#145](https://github.com/JLaborda/SmartWealthAI/issues/145).
