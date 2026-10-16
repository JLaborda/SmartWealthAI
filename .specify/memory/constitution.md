<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Modified principles:
  - I. Spec-Before-Code — added Living Spec persistence default
- Added sections: none (Sources of Truth rewritten in place)
- Removed / replaced:
  - "do not mass-migrate" dual-canon wording → single delivery tree under specs/
  - Incorrect claim that delivery SDD lives under .specify/
- Follow-up TODOs: none
-->

# SmartWealthAI Constitution

## Core Principles

### I. Spec-Before-Code

New features MUST follow Spec Kit before implementation:
`/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.

Feature delivery artifacts live under `specs/<###-slug>/` (`spec.md`, and
`plan.md` / `tasks.md` when created). Optional discovery uses assess under
`.specify/assessments/`; small bugs MAY use the bug extension under
`.specify/bugs/` or a lightweight path. Typos, CI one-liners, and equivalent
drive-bys MUST NOT require a full SDD loop.

**Persistence (Living Spec):** For an existing feature folder, revise
`spec.md` in place when intended behavior changes, then align or regenerate
`plan.md` / `tasks.md`. Use Flow-forward (a new `specs/<###-…>/` directory)
only when the change is a new product slice or clearly supersedes prior
scope. Do not rewrite historical spec bodies to the Spec Kit template unless
that feature is being actively changed.

No orphan features: if work lacks a matching feature document, draft the
minimal Spec Kit artifact first, then implement. After delivery, update
implementation status and acceptance criteria on the owning `spec.md`.

### II. Domain Boundaries

SmartWealthAI is a domain-first portfolio monorepo (`CONTEXT-MAP.md`).

- `investing/` and `credit/` MUST NOT share domain language or couple domain
  models. Do not reuse investing terms for credit (or the reverse).
- Domain code lives under `investing/src/investing/` and `credit/src/credit/`.
  Do not introduce root shared domain layers (`ingest/`, `benchmarks/`,
  `serving/`, etc.) as peers of domains. Root `notebooks/` is not canonical.
- Phase 2 Quantitative Value is cancelled for active execution
  ([ADR-0003](../../docs/adr/0003-phase2-qv-cancelled.md)). Prefer updating
  specs over writing new investing QV code.

### III. English Artifacts

All project artifacts MUST be written in English: source, comments,
docstrings, specs, commits, and PR text. Chat may use other languages;
deliverables remain English unless the user explicitly requests otherwise
for a specific artifact.

### IV. Tooling & Quality Gates

- **Runtime:** Python 3.11+ (`requires-python` in root `pyproject.toml`).
- **Packaging:** uv workspace; members `credit` + `investing`
  ([ADR-0005](../../docs/adr/0005-poetry-to-uv-workspace.md)). CI and Make
  MUST use `uv sync --frozen` so installs match `uv.lock`.
- **Gates:** `make lint` (ruff check + format check) and `make test` /
  domain targets as defined in `Makefile` and
  `.github/workflows/pr-ci.yml` MUST pass for mergeable work.
- **TDD:** Prefer test-first for non-trivial logic. Non-trivial changes MUST
  leave at least one runnable check that fails if the logic breaks.
- **Ponytail:** Apply YAGNI and stdlib/existing-deps first
  (`.cursor/rules/ponytail.mdc`). Do NOT skip validation at trust
  boundaries, data-loss prevention, or security.

### V. Protected Git Workflow

`develop` and `main` are protected. Do NOT commit on them or push to them.

Required flow: update `develop` → branch `cursor/<topic>` or `feat/…` →
commit on the branch → PR into `develop`. Details:
`.cursor/rules/branch-pr-workflow.mdc`.

## Sources of Truth & Constraints

### Documentation layers

| Layer | Location | Role |
| --- | --- | --- |
| Feature delivery (Spec Kit) | `specs/<###-slug>/` | Canonical feature specs, plans, tasks |
| Spec Kit tooling | `.specify/` | Templates, scripts, constitution memory, assessments, bugs |
| Domain glossaries / vision | `CONTEXT-MAP.md`, `investing/CONTEXT.md`, `credit/CONTEXT.md`, `investing/docs/architecture/` | Ubiquitous language and frozen investing vision |
| Operator guides | `investing/docs/guides/`, `credit/docs/guides/` | How to run tools (not feature specs) |
| Hard decisions | `docs/adr/` | Accepted ADRs |
| Agent runtime guidance | `AGENTS.md`, `.cursor/rules/` | Day-to-day agent instructions |

All feature specs MUST live under `specs/`. Spec Kit feature folders SHOULD
link to glossaries, architecture, guides, and ADRs when those remain the
detailed non-feature source. Do not duplicate glossary or ADR content into
`spec.md`.

### Secrets

Never commit secrets: `.env`, API keys (`SIMFIN_API_KEY`, etc.), credentials,
or personal finance / raw broker exports. Use env injection, CI secrets, or
AWS Secrets Manager as documented in `AGENTS.md`.

### Issues and PRs

- GitHub Issues that track feature work MUST link the relevant
  `specs/<###-slug>/` path (and related domain CONTEXT/ADR when useful).
- PRs MUST reference the applicable `spec.md` and `plan.md` when the change
  is Spec Kit–driven.

## Compliance References

Procedures live in existing files; this constitution does not restate them:

- Spec workflow: `.cursor/rules/spec-driven-workflow.mdc`, Spec Kit skills
- Branch/PR: `.cursor/rules/branch-pr-workflow.mdc`
- Language: `.cursor/rules/english-language.mdc`
- Simplicity: `.cursor/rules/ponytail.mdc`
- Phase and doc map: `AGENTS.md`, `CONTEXT-MAP.md`,
  `.cursor/rules/project-context.mdc`
- Feature index: `specs/README.md`
- Quality commands: `Makefile`, `.github/workflows/pr-ci.yml`
- Packaging: [ADR-0005](../../docs/adr/0005-poetry-to-uv-workspace.md)

## Governance

This constitution is the governance baseline for Spec Kit work in this repo.
Day-to-day agent instructions in `AGENTS.md` and `.cursor/rules/` MUST remain
consistent with these principles; if they conflict, amend this constitution
or update those files in a deliberate follow-up — do not silently diverge.

**Amendments:** Change `.specify/memory/constitution.md` via PR into
`develop`. Record version, rationale, and date in the version line.

**Versioning:** Semantic versioning for governance text:

- MAJOR — remove or redefine a principle incompatibly
- MINOR — add or materially expand a principle/section
- PATCH — clarification, wording, non-semantic refinement

**Compliance review:** PRs and reviews SHOULD check that scope respects
domain boundaries, has an owning spec when required, keeps secrets out of
git, and passes lint/test gates. Complexity beyond ponytail MUST be
justified in the PR or linked plan.

**Version**: 1.1.0 | **Ratified**: 2026-10-16 | **Last Amended**: 2026-10-16
