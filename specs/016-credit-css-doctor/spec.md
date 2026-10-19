> **Spec Kit:** [`specs/016-credit-css-doctor/spec.md`](./spec.md) — Living Spec.
> **Domain:** credit · **Lifecycle:** done
> **Glossary:** [`credit/CONTEXT.md`](../../credit/CONTEXT.md) · Map: [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md)
> **Assessment:** [`.specify/assessments/credit-css-doctor/`](../../.specify/assessments/credit-css-doctor/) · Decision: go (Option A)
> **GitHub:** [#191](https://github.com/JLaborda/SmartWealthAI/issues/191)

---

# Feature Specification: credit-css doctor (local readiness snapshot)

**Feature Branch**: `016-credit-css-doctor` (git: `cursor/credit-css-doctor`)

**Created**: 2026-10-19

**Status**: done — `credit-css doctor` + hermetic CliRunner tests green (#191)

**Code:** `credit/src/credit/cli.py` (`doctor`) · Tests: `credit/tests/test_cli_doctor.py`  
**Input**: Assessment handoff Option A from `.specify/assessments/credit-css-doctor/decision.md` (#191): local `credit-css doctor` readiness snapshot (identity + path/env booleans only; no secrets; no network; hermetic secret-safety check).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Early local readiness snapshot (Priority: P1)

As a CSS operator (or delivery agent), I want a single local action that shows whether the credit package and credit-related environment look ready, so I can catch misconfiguration before heavier scoring or data stages—without risking secret leakage.

**Why this priority**: Core operator value and the primary acceptance surface for #191.

**Independent Test**: Run the credit CLI `doctor` command with no network and no application data files required; confirm the report includes identity fields and presence booleans, and that no secret values appear.

**Acceptance Scenarios**:

1. **Given** a working credit CLI install, **When** the operator runs `doctor`, **Then** the report includes package version, Python version, and current working directory.
2. **Given** the closed path checklist, **When** `doctor` runs, **Then** each listed location is reported only as present or absent (existence check only; no file contents read).
3. **Given** credit-related environment configuration, **When** `doctor` runs, **Then** each listed signal is reported only as set/unset and (where applicable) referenced-file exists/missing—never the variable value or path string.
4. **Given** missing optional paths or unset env vars, **When** `doctor` runs, **Then** the command still completes successfully after printing the report (report-only; non-zero exit is not required for absences).

---

### User Story 2 - Secret-safe automated check (Priority: P1)

As a maintainer, I want an automated check that fails if the readiness report would expose secret material, so the diagnostic stays safe in CI and demos.

**Why this priority**: Security constraint is non-negotiable for this feature.

**Independent Test**: Run the hermetic automated check with a fake secret value present in the environment; assert the command output does not contain that value (or the configured artifact path string).

**Acceptance Scenarios**:

1. **Given** an environment variable under the closed checklist is set to a distinctive secret-like string, **When** `doctor` runs under the automated check, **Then** that string does not appear in the output.
2. **Given** an artifact path env is set to a distinctive path string, **When** `doctor` runs under the automated check, **Then** the path string does not appear in the output (only booleans for set / file-exists).

---

### User Story 3 - Spec Kit practice slice stays bounded (Priority: P2)

As a maintainer, I want this feature delivered only as a thin diagnostic slice so Spec Kit assess→specify→plan→tasks→implement can complete without expanding into mart, scoring, or cloud work.

**Why this priority**: Secondary but explicit driver of #191; guards scope.

**Independent Test**: Review the Living Spec and delivered surface: only the `doctor` command and its test/docs updates; no mart/scoring/AWS changes.

**Acceptance Scenarios**:

1. **Given** this feature is marked done, **When** the change set is reviewed, **Then** it does not alter scoring, mart transforms, model fit, PSI, or cloud/serve infrastructure beyond documenting the new command if needed.

---

### Edge Cases

- Expected data locations are absent (fresh clone, no LFS/raw extracts): report shows absent; command still succeeds.
- Artifact env unset: report shows unset and file-exists false (or N/A equivalent as “not set”); no error required.
- Artifact env set but file missing: report shows set true and file-exists false; still exit success.
- Operator runs from an unusual working directory: cwd is reported as-is; path presence checks use the closed relative/repo-rooted locations defined in Assumptions (not “whatever is under cwd”).
- Investing / SIMFIN variables are set: they MUST NOT appear in the report.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operators MUST be able to invoke a local credit CLI command named `doctor` that prints a human-readable readiness snapshot to standard output.
- **FR-002**: The snapshot MUST include: credit package version, Python version, and current working directory.
- **FR-003**: The snapshot MUST report presence/absence (boolean only) for this closed path checklist: the book-sample credit data directory (`credit/data/`) and the competition raw root (`data/credit/raw/`). Existence only—no reading of pickle/parquet/CSV contents.
- **FR-004**: The snapshot MUST report, as separate booleans and without printing values or path strings: whether `CREDIT_PIPELINE_ARTIFACT` is set, and whether the referenced path exists as a file when set.
- **FR-005**: The snapshot MUST NOT report investing-domain or SIMFIN configuration, and MUST NOT perform network calls.
- **FR-006**: When checklist items are missing or unset, `doctor` MUST still complete with a successful exit after printing the report (report-only policy).
- **FR-007**: The feature MUST include at least one automated check proving secret values and artifact path strings do not appear in `doctor` output.
- **FR-008**: Machine-readable (`--json`) output is OUT OF SCOPE for this delivery; may be added later via Living Spec edit on this same feature folder.

### Key Entities

- **Readiness Snapshot**: A one-shot, human-readable report of identity fields and boolean presence signals for a closed checklist; contains no secret values and no resolved secret path strings.
- **Closed Checklist**: The fixed set of paths and credit env signals listed in FR-003 and FR-004; not an extensible plugin surface in v1.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can obtain a complete readiness snapshot (identity + closed checklist booleans) in under one minute without reading application data files.
- **SC-002**: Automated checks for this feature fail if a planted secret value or artifact path string appears in the snapshot output (zero tolerance in CI for that assertion).
- **SC-003**: Delivery of this feature does not require changes to scoring, mart construction, model fit, PSI, or cloud serving to meet acceptance.
- **SC-004**: After delivery, this Living Spec can be marked done with FR-001–FR-007 satisfied and out-of-scope items still excluded.

## Assumptions

- Command name is `doctor` on the existing credit CSS CLI (Option A from assessment).
- Report-only exit policy: successful completion after printing even when items are absent/unset.
- Permanent thin operator tool: keep after Spec Kit practice; may be deleted later without mart coupling.
- Optional `CREDIT_API_HOST` / `CREDIT_API_PORT` are omitted from v1 to keep the checklist tiny (they have defaults in serve and are not required for local readiness).
- Path checks are existence-only against repo-relative locations above; they do not validate schema or file size.
- No new third-party dependencies.
- Assessment trail remains under `.specify/assessments/credit-css-doctor/` as discovery audit; this folder is the delivery Living Spec.

## Out of Scope

- Scoring, mart transforms, model fit, PSI behavior changes
- Network or remote health checks
- Printing secret values or secret path strings as values
- `--json` / structured machine-readable output (defer)
- SIMFIN / investing env
- New packaging or a separate diagnostics product

## Implementation status

**done** — `doctor` on `credit-css` CLI; contract labels in [contracts/doctor-cli.md](./contracts/doctor-cli.md); tests in `credit/tests/test_cli_doctor.py`. Plan: [plan.md](./plan.md) · Tasks: [tasks.md](./tasks.md).
