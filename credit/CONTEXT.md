# Credit risk (application credit scoring)

Ubiquitous language for the credit domain module (`credit/`). See [`CONTEXT-MAP.md`](../CONTEXT-MAP.md). This glossary is domain-only — no AWS, CLI, or library names.

## Language

**CSS (Credit Scoring System)**:
The end-to-end application credit scoring capability in this portfolio: data mart → features/bins → model → credit score → monitoring. Named as in Elliot Taehun Kim (2026), *Financial AI in Practice* (author shorthand for the system — not a universal industry acronym like PD or LGD).
_Avoid_: using “CSS” in UI copy without expanding it once (collision with Cascading Style Sheets in web/tech contexts); assuming every interviewer knows the acronym; blending with fraud detection

**Scorecard**:
The interpretable scoring artifact (bins, points, often logistic under the hood) that maps applicant attributes to a **credit score**. Chapter 6’s OptBinning path produces a scorecard; chapter 5’s scratch model can still emit a score without being a classic scorecard.
_Avoid_: calling any ML model a scorecard; credit report (bureau file)

**Credit score**:
A scaled numeric output derived from predicted default risk (probability → points), used to **rank** applicants by default risk in the demo — not a FICO® bureau score. **v1 scaling follows the book notebook** (pdo / base score / base odds once recovered from chapter 5 materials). Later we may refit scaling on a larger mart; v1 does **not** apply an approve/decline cutoff (optional profit/risk cutoff later).
_Avoid_: FICO score, credit rating (agency), ROC/EY ranks from investing; treating the CSS as an agent–client assignment optimizer; implying the demo score is a production bureau score; inventing “optimal” pdo without documenting the book baseline first

**Discrimination metrics (holdout)**:
Minimum reported quality of ranking **bad** vs **good** on holdout: **AUC-ROC** and **KS** (Kolmogorov–Smirnov). Optional later: Gini (= 2·AUC − 1).
_Avoid_: accuracy alone on imbalanced defaults; investing Sharpe as a credit metric

**Application scoring**:
Scoring at credit **origination** (approve / decline / terms), using application and bureau-like attributes available at decision time.
_Avoid_: behaviour scoring (post-booking), fraud scoring, collection scoring

**Application mart**:
The modeling table for one applicant (or application) per row: attributes knowable at decision time plus the binary **target**. Built by the CSS data stage from the demo dataset.
_Avoid_: raw provider dump; investing curated fundamentals

**Target**:
The binary outcome column in the **application mart** used for supervised learning (default vs not). Provider name kept in raw/mart schemas; domain interpretation is **bad** vs **good**.
_Avoid_: treating any feature as the label; multi-class targets in v1

**Bad (default event)**:
The positive class of the dataset’s binary **target** (default / serious credit failure as defined by that dataset’s dictionary). In code the column may be named `TARGET` or similar; in domain language the positive class is **bad**.
_Avoid_: inventing a bank policy (e.g. “90 DPD”) that the demo dataset does not encode; calling the label “fraud”; investing “permanent loss”

**Good**:
The negative class of the same **target** (no default event under the dataset’s definition).
_Avoid_: “approved” (origination decision) as a substitute for the outcome label

**Train/test split (application scoring)**:
Partition of the **application mart** into develop and holdout sets before WOE fitting and model training. **Time-based** on application/decision date when available; otherwise stratified random split with the limitation documented on the mart README. WOE/IV, OptBinning, and model fit use develop only.
_Avoid_: fitting WOE/IV or OptBinning on the holdout; using post-decision future features; implying a random Kaggle split is production-grade when a decision date exists

**Probability-to-score scaling**:
Deterministic map from predicted default probability to **credit score** points (pdo, base score, base odds). **v1 uses the book chapter 5 parameters** once available from the notebooks/sample; enlarging the mart and re-estimating those parameters is a later improvement.
_Avoid_: claiming calibrated “optimal” banking params without a documented baseline; skipping PD and only shipping a black-box ranker with no score points in chapter 5


**Data drift (batch monitoring)**:
A check that the **distribution** of application-mart features (or scores) in a recent batch has shifted relative to a **reference batch** (usually the develop/train window). In CSS v1 this is a local batch job, not online streaming detection.
_Avoid_: calling any metric drop “drift”; model decay / concept drift without saying so; implying live production alerting

**PSI (Population Stability Index)**:
The v1 **data drift** statistic comparing feature (or score) distributions between a reference batch and a recent batch; reported with a simple threshold for “stable / shift / severe”. Output is a local report artifact (file); cloud publish is later.
_Avoid_: treating PSI as a substitute for AUC/KS; using PSI on the holdout label as a performance metric; KS as a synonym for PSI


**Risk drivers (v1)**:
The top-k application-mart attributes highlighted after scoring to support a human-readable “why this **credit score**” story. v1 drivers are model/WOE-based (e.g. gain or |WOE|), **not** SHAP. Exposed via a **separate** request from the score itself.
_Avoid_: calling v1 drivers SHAP; mixing approve/decline reasons with ranking drivers; implying causal legal explainability

## Flagged ambiguities

- **CSS** means Credit Scoring System here, not Cascading Style Sheets. Expand on first use in READMEs. Book-aligned shorthand — not guaranteed industry-wide acronym usage.
- Exact **bad**/**good** mapping is dataset-specific: document target column and default value on the mart README.
- **CSS v1 use of the score:** **rank applications by risk only** (no approve/decline). Optional later: fictional cutoff from a profit/risk trade-off. Out of scope: assignment/matching engines.
- **Score scaling:** book notebook parameters preferred when available; **Friday demo may ship documented interim textbook defaults** (pdo/base_score/base_odds) until book values are pasted; optimizing pdo/base on a larger database is explicitly later.
- **Monitoring v1:** **PSI** on batches is the demo drift check; SHAP/cloud alarms are optional/later.
- **Explainability v1:** score and **risk drivers** are separate API calls; SHAP is optional/later stretch.

## Sources

Credit provenance (full portfolio list: [`CONTEXT-MAP.md`](../CONTEXT-MAP.md)):

1. **Elliot Taehun Kim (2026)** — *Financial AI in Practice: A Playbook for Credit, Fraud, and Investment Systems*
   Architecture patterns, feature engineering, and ML pipelines for credit risk, fraud, and investment systems (CSS v1 follows chapters 5–6).

**Demo datasets** (not live bank BFSI data): book sample (`train_df_sample.pkl` after LFS) for smoke / notebook fidelity; **raw competition extracts** from **AMEX Default Prediction** and **Home Credit Default Risk** (official Kaggle downloads, local only) for serious EDA and modeling; **FICO HELOC** later (explainability / fallback). Document **target** → **bad**/**good** on the mart README. Access-only — no competition submissions as a CSS goal.

**Raw competition extract**:
Local, gitignored official contest files under the credit raw layout, before they become an **application mart**. Not an investing-style data lake and not a community redistributed encoding of the contest.
_Avoid_: calling this the SimFin/investing lake; treating community parquet/feather mirrors as the source of truth; implying live bank BFSI data
