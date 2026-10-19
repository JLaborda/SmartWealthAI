# Concept: Local credit readiness snapshot

- **Slug**: credit-css-doctor
- **Created**: 2026-10-16
- **Recommended option**: Option A — credit-css doctor CLI

## Options

### Option A — credit-css doctor CLI
- **Sketch**: Operators run one local credit CLI subcommand (working name `doctor`) that prints a short human-readable readiness snapshot: package version, Python version, current working directory, whether a small closed set of expected data locations exist (yes/no only), and whether known credit env vars are set (yes/no only — never values or path strings). No data is read; no network. A hermetic automated check proves the report stays secret-safe. This also serves as the Spec Kit practice delivery slice (#191).
- **Appetite**: small
- **Trade-offs**: Wins a single early action and a clean Spec Kit dry-run target. Sacrifices depth (not a full health system). Risk: weak organic demand means the feature may be kept mainly for process practice; mitigated by deletable/small surface and Living Spec if later dropped or extended (`--json`).
- **Rabbit holes**: Expanding the checklist to every path/env in the monorepo; adding JSON/remote checks; printing resolved artifact paths “for helpfulness”; failing CI when local demo data is absent; coupling to investing/SIMFIN.

### Option B — Do nothing (keep status quo)
- **Sketch**: Rely on existing `credit-css --version`, README/guides, and late failures from fit/score/serve when env or artifacts are wrong. Spec Kit practice uses a different slice or is deferred.
- **Appetite**: small (zero build)
- **Trade-offs**: Wins YAGNI and avoids permanent CLI surface for thin demand. Sacrifices the early secret-safe readiness view and this particular dry-run vehicle; ad-hoc `echo $VAR` risk remains.
- **Rabbit holes**: None for product; opportunity cost is picking a larger or messier Spec Kit exercise later.

### Option C — Docs-only readiness checklist
- **Sketch**: Publish a short operator checklist (markdown) listing which version/env/path signals to verify manually, with explicit “do not print secret values” guidance. No new command.
- **Appetite**: small
- **Trade-offs**: Wins documentation with almost no code. Sacrifices one-action convenience and a hermetic secret-safety test of an actual report; weaker Spec Kit “implement” practice (docs-only).
- **Rabbit holes**: Checklist drift vs real code; operators still inspect env manually and may paste secrets into chat/logs.

## Recommendation

**Option A.** It is the smallest build that meets both problem goals: a one-action secret-safe readiness snapshot *and* a bounded Spec Kit delivery slice that stays off mart/scoring/AWS. Option B fails the Spec Kit practice goal for this issue; Option C under-delivers the “one local action + automated secret-safety check” metrics. Appetite stays **small**; open checklist/exit-policy questions must be closed in specify with defaults, not by growing scope.

## Out of Scope (for the recommended option)

- Scoring, mart transforms, model fit, PSI changes
- Network / remote health checks
- Printing secret values or secret path strings as values
- Machine-readable `--json` (defer to Living Spec)
- Investing / SIMFIN env
- Broad observability or multi-user product validation
- New dependencies or a separate diagnostics package

## Assumptions to Validate

- A closed v1 checklist is enough: at least package + Python identity, cwd, presence of documented credit data roots (existence only), and boolean presence of `CREDIT_PIPELINE_ARTIFACT` (and optionally whether the referenced file exists — still without printing the path); optional `CREDIT_API_*` only if specify keeps the list tiny.
- Report-only success (exit 0 after printing) is acceptable for v1 unless specify chooses fail-on-missing.
- Keeping the command as a permanent thin operator tool is fine; if it proves useless it can be deleted without mart coupling.
- Spec Kit specify/plan/tasks/implement for this option stays within appetite **small** (one command surface + one test + Living Spec update).
