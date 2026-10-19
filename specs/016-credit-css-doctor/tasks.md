# Tasks: credit-css doctor (local readiness snapshot)

**Input**: Design documents from `specs/016-credit-css-doctor/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/doctor-cli.md](./contracts/doctor-cli.md), [quickstart.md](./quickstart.md)

**Tests**: Included — FR-007 / User Story 2 require a hermetic secret-safety check (TDD: fail first).

**Organization**: By user story (US1 readiness report, US2 secret-safety, US3 scope guard). Existing monorepo — no greenfield project init.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 from spec.md
- Include exact file paths in descriptions

## Path Conventions

Credit domain package: `credit/src/credit/`, tests: `credit/tests/` (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm delivery context on the feature branch (repo already exists).

- [x] T001 Confirm branch `cursor/credit-css-doctor` and that `from credit.cli import main` works under `uv run --package credit` (no new packaging)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Lock the closed checklist before implementing `doctor` (matches data-model + contract).

**⚠️ CRITICAL**: No user story work until this is done.

- [x] T002 Record closed checklist constants for implementation (dirs `credit/data`, `data/credit/raw`; env name `CREDIT_PIPELINE_ARTIFACT` as string literal — do not import `credit.api`) aligned with `specs/016-credit-css-doctor/contracts/doctor-cli.md` and `specs/016-credit-css-doctor/data-model.md`

**Checkpoint**: Foundation ready — US1/US2/US3 can proceed

---

## Phase 3: User Story 1 - Early local readiness snapshot (Priority: P1) 🎯 MVP

**Goal**: `credit-css doctor` prints identity + path/env booleans per contract; exit 0 (report-only).

**Independent Test**: `uv run credit-css doctor` from repo root → exit 0; all contract labels present with `yes`/`no` booleans.

### Tests for User Story 1

> Write FIRST; ensure they FAIL before implementation.

- [x] T003 [P] [US1] Add failing CliRunner tests in `credit/tests/test_cli_doctor.py` asserting exit 0 and labels `package_version:`, `python_version:`, `cwd:`, `path_credit_data:`, `path_competition_raw:`, `env_CREDIT_PIPELINE_ARTIFACT_set:`, `env_CREDIT_PIPELINE_ARTIFACT_file_exists:` (booleans `yes`/`no` only) per `specs/016-credit-css-doctor/contracts/doctor-cli.md`

### Implementation for User Story 1

- [x] T004 [US1] Implement `@main.command("doctor")` in `credit/src/credit/cli.py` emitting the Readiness Snapshot fields from `specs/016-credit-css-doctor/data-model.md` (path checks: `Path.cwd() / "credit/data"` and `Path.cwd() / "data/credit/raw"` as directories; env set + file-exists without printing values/paths; always exit 0 after print)
- [x] T005 [US1] Update Click group help / default stage listing in `credit/src/credit/cli.py` to include `doctor` (same pattern as `psi`)
- [x] T006 [US1] Make T003 tests pass via `uv run --package credit pytest credit/tests/test_cli_doctor.py -q`

**Checkpoint**: US1 independently usable (`doctor` report matches contract)

---

## Phase 4: User Story 2 - Secret-safe automated check (Priority: P1)

**Goal**: Automated check fails if secret/path strings leak into doctor output.

**Independent Test**: Plant `CREDIT_PIPELINE_ARTIFACT=/tmp/doctor-secret-path-XYZ/pipeline.joblib`; assert output has set=yes, file_exists=no, and does not contain `doctor-secret-path-XYZ`.

### Tests for User Story 2

- [x] T007 [P] [US2] Extend `credit/tests/test_cli_doctor.py` with failing (then passing) secret/path non-leak assertions per contract Test contract section (FR-007)

### Implementation for User Story 2

- [x] T008 [US2] Verify `credit/src/credit/cli.py` `doctor` never echoes env value or resolved path; fix if T007 fails; keep report-only exit 0

**Checkpoint**: US1 + US2 green; FR-007 satisfied

---

## Phase 5: User Story 3 - Spec Kit practice slice stays bounded (Priority: P2)

**Goal**: Delivery stays off mart/scoring/PSI/AWS; Living Spec can close.

**Independent Test**: Diff touches only CLI/test/(optional README) + `specs/016-credit-css-doctor/` (+ assessment trail if committed); no mart/scoring/AWS code changes.

- [x] T009 [US3] Confirm change set does not modify mart/scoring/PSI/serve/AWS modules; adjust `credit/tests/test_cli_stub.py` only if default help listing assertions require `doctor`
- [x] T010 [US3] Update `specs/016-credit-css-doctor/spec.md` implementation status to done and lifecycle header; note code/test paths

**Checkpoint**: All stories independently satisfied; ready for polish

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Operator docs + quickstart validation

- [x] T011 [P] Optional one-line mention of `doctor` in `credit/README.md` operator commands (docs-only; skip if help already sufficient)
- [x] T012 Run `specs/016-credit-css-doctor/quickstart.md` validation (`uv run credit-css doctor` + pytest) and fix any contract drift in `credit/src/credit/cli.py` or `credit/tests/test_cli_doctor.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Immediate
- **Foundational (Phase 2)**: After Setup — BLOCKS stories
- **US1 (Phase 3)**: After Foundational — MVP
- **US2 (Phase 4)**: After US1 implementation exists (extends same test file + same command); can draft T007 tests in parallel with T003 but T008 needs T004
- **US3 (Phase 5)**: After US1+US2 green
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3
- **US2 (P1)**: Shares `doctor` from US1; secret-safety is additive assertions
- **US3 (P2)**: Review/docs after functional work

### Within Each User Story

- Tests FAIL before implementation (T003 before T004; T007 before/with T008)
- Help listing (T005) after command exists
- Spec status (T010) last among delivery tasks

### Parallel Opportunities

- T003 and T007 can be authored together in `credit/tests/test_cli_doctor.py` (single author preferred to avoid merge conflict — mark [P] only if split carefully)
- T011 docs parallel with T012 once code is stable

---

## Parallel Example: User Story 1

```bash
# After T002: write failing tests, then implement command
# Task T003: credit/tests/test_cli_doctor.py (failing contract labels)
# Task T004: credit/src/credit/cli.py doctor command
# Task T005: credit/src/credit/cli.py help listing
# Task T006: pytest credit/tests/test_cli_doctor.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 → T002  
2. T003 → T004 → T005 → T006  
3. **STOP and VALIDATE**: `uv run credit-css doctor` + pytest  
4. Then US2 (T007–T008) before calling the feature done (FR-007 is P1)

### Incremental Delivery

1. Setup + Foundational  
2. US1 → manual doctor works  
3. US2 → secret-safety CI gate  
4. US3 → spec done + scope check  
5. Polish → README/quickstart  

### Suggested MVP scope

**US1 + US2** (both P1). US3 + polish close the Spec Kit loop.

---

## Notes

- Do not import `credit.api` from `doctor` (FastAPI stack) — use env name string literal (research.md).
- No new dependencies; no `--json`.
- Commit on `cursor/credit-css-doctor` only; PR into `develop`.
