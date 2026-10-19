# Idea Research: credit-css doctor diagnostics

- **Slug**: credit-css-doctor
- **Created**: 2026-10-16
- **Evidence confidence (overall)**: medium

## Users & Demand

- Stated demand is from a single GitHub issue authored for this workstream: operators/agents want a zero-risk local check before heavier CSS commands — [source: https://github.com/JLaborda/SmartWealthAI/issues/191] (confidence: high for *stated* intent; low for *observed* multi-user demand).
- No prior support tickets, usage metrics, or secondary reporters found in-repo for a missing `doctor` command — [ASSUMPTION: absence of other issues/docs mentioning `doctor` implies demand is not yet validated beyond the author] (confidence: medium).
- Issue labels `enhancement` + `ready-for-agent` indicate maintainer intent to treat this as agent-executable scope, not an open product discovery — [source: https://github.com/JLaborda/SmartWealthAI/issues/191] (confidence: high).
- Primary driver recorded in intake/issue is Spec Kit end-to-end dry run; operator smoke check is secondary — [source: `.specify/assessments/credit-css-doctor/intake.md`; https://github.com/JLaborda/SmartWealthAI/issues/191] (confidence: high).

## Prior Art

- **No `doctor` (or equivalent diagnostics) subcommand** on the current Click group; help lists mart/fit/score/psi stages only — [source: `credit/src/credit/cli.py`] (confidence: high).
- **Partial substitute already ships:** `@click.version_option` / `credit-css --version` and package `__version__` are tested — [source: `credit/src/credit/cli.py`; `credit/tests/test_cli_stub.py`] (confidence: high).
- **CLI extension pattern is established:** Click group + hermetic `CliRunner` tests for stub, mart, fit/score, psi — [source: `credit/tests/test_cli_stub.py`; `credit/tests/test_psi.py`; related CLI tests] (confidence: high).
- **Known credit env vars in code:** `CREDIT_PIPELINE_ARTIFACT` (required for serve; failure if unset/missing file); optional `CREDIT_API_HOST` / `CREDIT_API_PORT` with defaults; MLflow uses `MLFLOW_TRACKING_URI` (shared tooling, not credit-domain-only) — [source: `credit/src/credit/api.py`; `credit/src/credit/mlflow_logging.py`; `credit/docs/guides/serve-fastapi.md`] (confidence: high).
- **Expected data layout is documented** (existence checks would map here, not invented paths): book sample under `credit/data/`; competition raw under gitignored `data/credit/raw/...` — [source: `credit/data/README.md`] (confidence: high).
- **No Spec Kit feature folder** yet for doctor; next sequential feature number is 016 per index — [source: `specs/README.md`] (confidence: high).
- External “doctor” CLIs (e.g. package health commands in other ecosystems) not surveyed for this portfolio slice — skipped as low relevance; [ASSUMPTION: no need to copy an external doctor UX for a demo monorepo] (confidence: low).

## Market & Context

- Alternatives operators use today: `credit-css --help` / `--version`, reading guides (`credit/README.md`, `credit/docs/guides/serve-fastapi.md`), and failing later inside `fit` / `score` / `credit-css-serve` when artifact/env is wrong — [source: `credit/README.md`; `credit/docs/guides/serve-fastapi.md`; https://github.com/JLaborda/SmartWealthAI/issues/191] (confidence: high).
- Cost of doing nothing: keep late failures and ad-hoc `echo $VAR` risk; Spec Kit practice would need another thin slice — [source: https://github.com/JLaborda/SmartWealthAI/issues/191] (confidence: medium).
- This is an internal portfolio/demo CSS tool, not a commercial product competing in a market — [ASSUMPTION] (confidence: high as project framing from constitution/`CONTEXT-MAP.md`).

## Data & Constraints

- Constitution requires Spec-before-code for features, English artifacts, uv/Python 3.11+, and **ponytail/YAGNI** (smallest thing; no new deps if avoidable) — [source: `.specify/memory/constitution.md`] (confidence: high).
- Security constraint from the idea itself: env/path reporting must be boolean-only; never print secret values (and issue says not secret *paths as values* either) — [source: https://github.com/JLaborda/SmartWealthAI/issues/191] (confidence: high).
- Domain boundary: credit-only; do not couple to investing/`SIMFIN_API_KEY` — [source: issue #191 out of scope; constitution Domain Boundaries] (confidence: high).
- Exact env/path checklist and exit-code policy remain open (carried from intake) — [source: `.specify/assessments/credit-css-doctor/intake.md`] (confidence: high that they are unresolved).

## Evidence Against the Idea

- **Weak organic demand:** only one authored issue; primary motive is workflow practice, not a measured operator pain — [source: https://github.com/JLaborda/SmartWealthAI/issues/191; intake.md] (confidence: high).
- **Partial overlap with existing tools:** `--version` already answers package identity; serve already fails clearly when `CREDIT_PIPELINE_ARTIFACT` is missing — [source: `credit/tests/test_cli_stub.py`; `credit/docs/guides/serve-fastapi.md`] (confidence: high).
- **YAGNI / ponytail tension:** a permanent CLI surface for a Spec Kit dry run may be disposable scaffolding dressed as a feature — [source: constitution Ponytail; issue “deletable scope”] (confidence: medium).
- **Ambiguous checklist risk:** without a closed list of paths/env vars, `doctor` can become an expanding kitchen-sink status command — [source: intake First-Glance Unknowns] (confidence: medium).

## Gaps & Open Questions

- [NEEDS CLARIFICATION: Which exact credit env vars and expected data paths should `doctor` report as present/absent?]
- [NEEDS CLARIFICATION: Should the command remain as a permanent operator tool after the Spec Kit dry run, or is it disposable scaffolding?]
- [NEEDS CLARIFICATION: What exit-code policy applies when paths or env vars are missing — always succeed after printing the report, or fail non-zero?]
- [NEEDS CLARIFICATION: Is presence of `CREDIT_PIPELINE_ARTIFACT` only “env set,” or also “path exists as a file” (without printing the path value)?]

## Sources

- https://github.com/JLaborda/SmartWealthAI/issues/191 (host: `github.com`, policy: allowlisted)
- `.specify/assessments/credit-css-doctor/intake.md` (local assessment artifact)
- `credit/src/credit/cli.py`
- `credit/src/credit/api.py`
- `credit/src/credit/mlflow_logging.py`
- `credit/tests/test_cli_stub.py`
- `credit/tests/test_psi.py`
- `credit/README.md`
- `credit/docs/guides/serve-fastapi.md`
- `credit/data/README.md`
- `specs/README.md`
- `.specify/memory/constitution.md`
