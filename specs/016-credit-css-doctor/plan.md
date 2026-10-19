# Implementation Plan: credit-css doctor (local readiness snapshot)

**Branch**: `cursor/credit-css-doctor` (feature id `016-credit-css-doctor`) | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-credit-css-doctor/spec.md` (#191, assessment Option A)

**Note**: Filled by `/speckit-plan`.

## Summary

Add a `credit-css doctor` Click subcommand that prints a human-readable readiness snapshot (package version, Python version, cwd, path existence booleans, `CREDIT_PIPELINE_ARTIFACT` set + file-exists booleans) without reading data files, printing secrets/path values, or calling the network. Deliver with one hermetic CliRunner test proving secret-safety. Touch only the credit CLI surface (+ test; optional one-line help/README). No mart, scoring, PSI, or AWS changes.

## Technical Context

**Language/Version**: Python 3.11+ (`requires-python` in root `pyproject.toml`)

**Primary Dependencies**: Existing only — Click (credit CLI), stdlib (`sys`, `os`, `pathlib`). No new packages.

**Storage**: N/A (existence checks only; no reads/writes of application data)

**Testing**: pytest + `click.testing.CliRunner` under `credit/tests/` (same pattern as `test_cli_stub.py`)

**Target Platform**: Local operator / CI (macOS, Linux, Dev Container); offline

**Project Type**: CLI subcommand on existing `credit-css` console script (`credit.cli:main`)

**Performance Goals**: Completes in well under one minute (trivial I/O); SC-001

**Constraints**: Boolean/identity-only output; never print env values or artifact path strings; report-only exit 0; credit-domain only (no SIMFIN); ponytail / YAGNI

**Scale/Scope**: One command + one test file (or addition to stub tests); closed checklist of two paths + one env (two booleans)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
| --- | --- | --- |
| I. Spec-Before-Code | PASS | Living Spec at `specs/016-credit-css-doctor/spec.md`; assessment trail under `.specify/assessments/credit-css-doctor/` |
| II. Domain Boundaries | PASS | Credit-only CLI; no investing/SIMFIN |
| III. English Artifacts | PASS | Spec, plan, research, contracts, tests in English |
| IV. Tooling & Quality Gates | PASS | uv workspace; pytest; no new deps; one runnable hermetic check |
| IV. Ponytail | PASS | Extend existing `cli.py`; stdlib + Click; no abstractions beyond one command |
| V. Protected Git Workflow | PASS | Work on `cursor/credit-css-doctor`; PR into `develop` (not commit on protected branches) |

**Post-design re-check**: PASS — design adds only `plan.md` siblings + contracts for CLI stdout; no unjustified complexity. Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/016-credit-css-doctor/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   └── doctor-cli.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
credit/src/credit/
├── cli.py               # Add @main.command("doctor"); update group help listing
├── __init__.py          # __version__ (existing)
└── api.py               # ARTIFACT_ENV name reference only (do not import FastAPI into doctor path)

credit/tests/
└── test_cli_doctor.py   # CliRunner: identity fields, booleans, secret/path not leaked, exit 0
```

**Structure Decision**: Extend the existing credit domain CLI package. No new package, no `services/` layer. Optional: one line in `credit/README.md` under operator commands (docs-only, not required for FR).

## Complexity Tracking

> No constitution violations requiring justification.
