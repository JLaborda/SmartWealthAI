# Research: credit-css doctor

**Feature**: `specs/016-credit-css-doctor`  
**Date**: 2026-10-19

## Decision: Implement as Click subcommand on existing `credit.cli:main`

- **Rationale**: Spec FR-001 names `doctor` on the credit CSS CLI; `cli.py` already hosts all operator stages; CliRunner tests are established (`test_cli_stub.py`, `test_psi.py`).
- **Alternatives considered**: Separate console script — rejected (new entry point + packaging noise). Docs-only checklist — rejected at assess (Option C). Do nothing — rejected (go verdict).

## Decision: Path checks relative to process cwd (operators run from repo root)

- **Rationale**: Spec assumes repo-relative locations (`credit/data/`, `data/credit/raw/`). Guides and Make targets already assume repo-root cwd. Existence via `Path.cwd() / "credit/data"` and `Path.cwd() / "data/credit/raw"` (directory exists). No filesystem walk / no package-relative heuristics (ponytail).
- **Alternatives considered**: Walk up to find `.git` — rejected (extra code, edge cases in worktrees). Package `files()` location — rejected (wrong for `data/credit/raw` gitignored layout).

## Decision: Env name as string literal matching `CREDIT_PIPELINE_ARTIFACT`

- **Rationale**: Same name as `credit.api.ARTIFACT_ENV` and operator guides. Avoid importing `credit.api` from `doctor` (pulls FastAPI/serving stack). Test may assert equality against `ARTIFACT_ENV` via a light import in the test only, or simply use the documented string.
- **Alternatives considered**: Move constant to a shared light module — deferred (YAGNI for one string). Import from `api` in CLI — rejected (heavy import for a diagnostic).

## Decision: Report format — labeled plain lines (human-readable)

- **Rationale**: Spec requires human-readable stdout; `--json` out of scope. Stable enough labels for tests (`package_version:`, `python_version:`, `cwd:`, `path_credit_data:`, `path_competition_raw:`, `env_CREDIT_PIPELINE_ARTIFACT_set:`, `env_CREDIT_PIPELINE_ARTIFACT_file_exists:`) with yes/no or true/false for booleans.
- **Alternatives considered**: Free-form prose paragraphs — harder to assert. JSON — out of scope FR-008.

## Decision: Artifact file-exists when unset → report `false` (or equivalent “no”)

- **Rationale**: Spec edge case: unset → unset + file-exists false; still exit 0. Single boolean column keeps contract simple.
- **Alternatives considered**: Print `n/a` when unset — acceptable synonym if documented in contract; prefer boolean `no`/`false` for one parsing style.

## Decision: One dedicated test module `credit/tests/test_cli_doctor.py`

- **Rationale**: Secret-safety and checklist assertions deserve a focused file; keeps `test_cli_stub.py` about the stub/help surface.
- **Alternatives considered**: Append to `test_cli_stub.py` — fine but noisier; either works. Prefer dedicated file for FR-007 clarity.

## Resolved clarifications

No remaining NEEDS CLARIFICATION from Technical Context — all choices grounded in spec Assumptions and assess decision defaults.
