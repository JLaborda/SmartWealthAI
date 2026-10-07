# Feature: Local PSI data-drift monitoring (CSS v1)

**Status:** done — Friday MUST (local green demo); hermetic tests green  
**GitHub:** Friday demo week (monitoring grill 2026-10-06) · parent CSS [#142](https://github.com/JLaborda/SmartWealthAI/issues/142)  
**Code:** `credit/src/credit/psi.py`, `credit/src/credit/cli.py` (`psi` command) · Tests: `tests/credit/test_psi.py` · Artifacts: `psi_report.md`, `psi_report.json`  
**Domain:** credit / CSS (Credit Scoring System)  
**Glossary:** [`../../CONTEXT.md`](../../CONTEXT.md) · Map: [`../../../CONTEXT-MAP.md`](../../../CONTEXT-MAP.md)  
**Related:** chapter 5 scoring [`css-chapter5-mart-and-scoring.md`](css-chapter5-mart-and-scoring.md) · operator guide [`../guides/friday-demo.md`](../guides/friday-demo.md)

## Problem Statement

The Friday demo must show a **batch data-drift** check: has the recent application batch shifted vs a reference window? Without a local **PSI** report, the CSS story stops at score + drivers and cannot demonstrate monitoring.

## Solution

Add a hermetic `credit-css psi` CLI that:

1. Reproduces the same develop/holdout split as `credit-css fit` from `--mart` + `--artifact` (default demo path).
2. Compares **reference** (develop) vs **recent** (holdout) on `credit_score` (+ optional `pd`) and the **top 10 features by IV** from the fitted pipeline.
3. Optionally forces a red drift demo via `--synthetic-drift` (shift/scale 1–2 top-IV features on a copy of recent, fixed seed).
4. Writes `psi_report.md` + `psi_report.json` under `--output-dir` with per-column PSI and stable / shift / severe labels.

## User Stories

1. As a risk stakeholder, I want a local PSI report comparing reference vs recent batches, so that distribution shift is visible without cloud tooling.
2. As a demo operator, I want a **stable** scenario (develop vs holdout from the same mart split as fit), so that the green path is honest.
3. As a demo operator, I want `--synthetic-drift` to push PSI into severe on shifted columns, so that the red path is reproducible.
4. As a developer, I want hermetic fixture tests (no `data/credit/` marts), so that CI stays offline.
5. As an operator, I want CLI-overridable PSI thresholds, so that demo defaults (0.10 / 0.25) can be tuned without code changes.

## Implementation Decisions

| Topic | Decision |
| --- | --- |
| Interactive HTML drift UI | **Out of this PR** (post-demo / optional later). No third-party drift dashboard library in v1. |
| Default batches | Reference = **develop**, recent = **holdout**, same stratified split as fit (`holdout_fraction`, `random_state`). |
| Overrides | Optional `--reference` / `--recent` paths replace the default batches (still need `--artifact` for IV ranking + scoring). |
| Columns | `credit_score`, optional `pd` (default on), plus up to **top 10** features by IV from `pipeline.wrap_notes["iv_by_feature"]` (fallback: `pipeline.feature_names` order). |
| Bins | **10 quantile bins from reference**; same edges applied to recent. **Not** WOE bins. |
| Thresholds (default) | PSI &lt; 0.10 → `stable`; 0.10–0.25 → `shift`; ≥ 0.25 → `severe`. CLI-overridable. |
| Synthetic drift | Copy recent; shift/scale **1–2** highest-IV raw features; fixed seed; recompute scores on the drifted recent so `credit_score`/`pd` can move too. |
| Artifacts | `psi_report.md` + `psi_report.json` under `--output-dir`. |
| CLI | `credit-css psi` — defaults `--mart` + `--artifact` + `--output-dir`; `--synthetic-drift` flag; threshold flags. |

### PSI formula (v1)

For each column, with reference proportions $e_i$ and recent proportions $a_i$ over the shared bin edges:

$$
\mathrm{PSI} = \sum_i (a_i - e_i) \ln\frac{a_i}{e_i}
$$

Zero / empty bins use a small epsilon so $\ln$ stays defined. Overall report label = worst label across columns (`severe` > `shift` > `stable`).

## Acceptance Criteria

- [x] Spec exists under `credit/docs/features/` before/with code (this file).
- [x] `credit-css psi --mart … --artifact … --output-dir …` writes both report files.
- [x] Stable scenario (hermetic `psi_mart` fixture, no synthetic drift): monitored columns labeled `stable`.
- [x] `--synthetic-drift`: shifted feature columns have PSI ≥ severe threshold (and higher than the same column in the stable run).
- [x] Hermetic tests under `tests/credit/`; no secrets; no committed `data/credit/` marts.
- [x] Operator notes in `credit/README.md` and `credit/docs/guides/friday-demo.md`.
- [x] Glossary: monitoring v1 = PSI file report; interactive visualization later (no library names).

## Testing Decisions

- Public seam: `run_psi_check(...)` (or equivalent) + thin CLI wrapper.
- Fixture: `tests/credit/fixtures/scoring_mart/applications.csv` → build mart → fit → psi.
- Assert report JSON schema keys, per-column labels for stable path, and elevated PSI under `--synthetic-drift`.

## Out of Scope

- Interactive HTML drift dashboards / third-party drift UIs
- Terraform / AWS publish of reports
- SHAP, SageMaker, concept-drift / performance monitoring beyond PSI
- Merging unrelated open PRs
- Using WOE bin edges for PSI (v1 uses reference quantile bins only)

## Further Notes

- Expand “CSS” on first README mention: Credit Scoring System.
- Frozen grill decisions (2026-10-06) must not be re-opened in this PR.
