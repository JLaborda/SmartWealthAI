# Decision: credit-css doctor diagnostics

- **Slug**: credit-css-doctor
- **Decided**: 2026-10-19
- **Verdict**: go
- **Artifacts reviewed**: intake.md | research.md | problem.md | concept.md

## Scorecard

| Criterion | Rating | Justification |
|-----------|--------|---------------|
| Problem validity | adequate | Late failure + secret-leak risk for operators is real; Spec Kit practice need is explicit in #191. Organic multi-user demand is thin (research). |
| Evidence strength | adequate | Repo prior art, env/path layout, and issue intent are well cited; overall research confidence medium; weak on observed usage demand, not on technical facts. |
| Value vs. inaction | adequate | Beats status quo for one-action secret-safe snapshot and this dry-run vehicle; incremental vs `--version`/serve errors alone (problem + research). |
| Feasibility / appetite | strong | Option A is small; Click + CliRunner patterns already exist (concept + research). |
| Strategic fit | strong | Credit-only, Spec-before-code practice, ponytail-sized, no mart/AWS; aligns with constitution and #191. |
| Risk posture | adequate | Rabbit holes named (checklist creep, printing paths, JSON/network); mitigated by closed out-of-scope and assumptions for specify defaults. |

## Verdict & Rationale

**go.** Problem validity and evidence are at least adequate; Option A is shaped within small appetite; strategic fit is strong for a Spec Kit dry run that also leaves a useful operator smoke check. Organic demand is weak enough that a **kill** would be defensible on YAGNI alone, but the dual goal (readiness + bounded assess→delivery practice) and explicit maintainer issue (#191, `ready-for-agent`) clear the bar. Remaining open questions are specification defaults, not blockers requiring a return to research/define.

## If go — Handoff to `/speckit-specify`

- **Problem**: Operators and agents lack an early, secret-safe way to confirm local credit package/env readiness before heavier CSS stages; maintainers also need a thin Spec Kit practice slice.
- **Chosen approach**: Option A — `credit-css doctor` CLI: human-readable snapshot (package version, Python version, cwd, path existence booleans, credit env set/file-exists booleans); no data reads; no network; hermetic secret-safety test.
- **In scope / out of scope**: In — one doctor subcommand, closed checklist, one automated check, Living Spec under next `specs/016-…`. Out — scoring/mart/fit/PSI, network, secret values or path strings as values, `--json`, SIMFIN/investing, new deps.
- **Success metrics**: Readiness snapshot in under one minute without reading application data; automated check that secrets never appear in output; Spec Kit Living Spec closable without mart/AWS creep.
- **Carried-forward open questions** (resolve with defaults in specify):
  - Exact closed checklist of paths/env (start from concept assumptions: credit data roots + `CREDIT_PIPELINE_ARTIFACT` set and/or file exists without printing path).
  - Permanent thin tool vs disposable (default: keep; deletable later).
  - Exit policy (default: report-only exit 0).
  - Env “set” vs “referenced file exists” for artifact (default: report both as separate booleans).
- **Related**: GitHub [#191](https://github.com/JLaborda/SmartWealthAI/issues/191); branch `cursor/credit-css-doctor`; assessment `.specify/assessments/credit-css-doctor/`.
