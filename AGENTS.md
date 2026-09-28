# AGENTS.md

Instructions for AI agents working in the SmartWealthAI repository.

## Project phase

SmartWealthAI is in **MVP planning and spec refinement**, with a **June 30, 2026 demo slice** as the current delivery target. Specifications live under `spec/`. Implementation work must align with a feature `spec.md` under `spec/features/` and respect cross-cutting rules in `spec/constitution/mission.md`.

Do not treat `src/` or `notebooks/` as canonical architecture; they are legacy exploration and out of scope for planning context.

## Documentation map (source of truth)

| Path | Purpose |
| --- | --- |
| `CONTEXT.md` | Ubiquitous language (domain terms; extend via `/grill-with-docs`) |
| `spec/adr/*.md` | Architecture Decision Records (hard-to-reverse choices) |
| `spec/constitution/roadmap.md` | June 30 delivery target (narrow vertical slice) |
| `spec/constitution/mission.md` | MVP vision, principles, module table, closed decisions |
| `spec/features/00N-slug/spec.md` | Per-module specs (scope, acceptance criteria); optional `plan.md` / `tasks.md` |
| `spec/constitution/tech-stack.md` | Technologies, infrastructure, runtime conventions |
| `spec/meta/github-issues.md` | GitHub Issues workflow for feature implementation |
| `spec/archive/requirements.md` | Sprint 0 spike (superseded by MVP specs; historical reference) |
| `spec/backlog/backlog.md` | Informal product ideas mapped to MVP features |
| `spec/README.md` | Index of the docs tree |

See also `.cursor/rules/*.mdc` for persistent agent guidance.

## Language

Write all code, comments, docstrings, documentation, commits, and PR text in **English**.

## Spec-driven workflow

1. Identify the feature spec (e.g. `spec/features/003-cheap-stocks/spec.md`).
2. Read `spec/constitution/mission.md` for constraints (point-in-time data, exclusions, MLflow, paper trading, etc.).
3. Resolve open questions in the spec; record decisions in the spec or architecture doc.
4. Implement only what the spec allows for the current phase.
5. After implementation, update the feature spec (implementation status, acceptance criteria, links to code when it exists).

## Runtime

- **Python:** 3.11+ (`requires-python = "^3.11"` in `pyproject.toml`)
- **Dependencies:** Poetry

```bash
poetry env use python3.11
poetry install
poetry run pytest
```

**Before every commit:** run `make format` (see `.cursor/rules/git-conventions.mdc`).

### MLflow (demo pipeline runs)

`mlflow-skinny` is a Poetry dependency (`poetry install` is enough for logging). No local MLflow UI server is required for #61.

```bash
export MLFLOW_TRACKING_URI="file://$(pwd)/mlruns"   # default if unset
export MLFLOW_ALLOW_FILE_STORE=true                 # required for file:// with MLflow 3.14+ (set automatically by score-universe)
```

Logged by `score-universe` after ranking/portfolio construction ([#61](https://github.com/JLaborda/SmartWealthAI/issues/61)).

To view runs on a remote tracking server (e.g. EC2 Docker), set `MLFLOW_TRACKING_URI` to that server **before** `score-universe` and use a shared artifact store (e.g. S3). Local `mlruns/` are not visible to a remote server unless you log there at run time.

### Fundamentals — demo path (SimFin)

Active pipeline for the June 30 demo slice. Requires `SIMFIN_API_KEY` (never commit).

**Local dev:** copy `.env.example` → `.env`, set the key, open a new terminal (devcontainer loads `.env` via `.devcontainer/install-env-hook.sh`). `.env` is gitignored.

**Cloud agents / CI:** do not rely on `.env` — inject `SIMFIN_API_KEY` via Cursor cloud agent secrets, GitHub Actions secrets (CI), or AWS Secrets Manager (runtime per architecture).

```bash
export SIMFIN_API_KEY="<from user secrets>"
poetry run download-simfin
```

Spec: [`spec/features/006-etl-data-lake/spec.md`](spec/features/006-etl-data-lake/spec.md). Operator guide: [`spec/guides/download-simfin.md`](spec/guides/download-simfin.md). Delivery target: [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md).

### Fundamentals — SEC spike (frozen, phase 2)

```bash
export SEC_IDENTITY="Your Name your@email.com"
poetry run download-fundamentals --universe dow30
```

Guide: [`spec/guides/download-fundamentals.md`](spec/guides/download-fundamentals.md).

## Gotchas

- `yfinance`, SimFin bulk API, and other data providers need network access.
- SimFin requires `SIMFIN_API_KEY` in the environment (AWS Secrets Manager at runtime).
- SEC EDGAR and `edgartools` require `SEC_IDENTITY` (real name + email) for the **frozen** SEC spike only.
- `data/` is gitignored except `data/reference/**` (versioned universe and mapping CSVs).
  Never commit personal finance files or raw broker exports.

## GitHub Issues (task tracking)

Git specs in `spec/` are canonical. **GitHub Issues** track feature implementation. See [`spec/meta/github-issues.md`](spec/meta/github-issues.md).

- **One issue per feature** when implementation starts.
- Issue body must link `spec/features/00N-slug/spec.md` (and `plan.md` / `tasks.md` when they exist).
- Label `ready-for-agent` when the spec is complete and work can start.
- On completion: update `spec.md` and `tasks.md`, then close the issue.

**Commit workflow:** `/commit_split` — project skill [`.cursor/skills/commit-split/SKILL.md`](.cursor/skills/commit-split/SKILL.md); splits into conventional commits; out-of-scope paths follow [`.gitignore`](.gitignore).

## Agent skills

Matt Pocock engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) are vendored under [`.cursor/skills/`](.cursor/skills/). They read repo-specific config from [`.cursor/rules/`](.cursor/rules/) (issue tracker, triage labels, domain layout).

### Issue tracker

GitHub Issues on `JLaborda/SmartWealthAI` via the `gh` CLI. MVP specs in `spec/` remain canonical. See [`.cursor/rules/issue-tracker.md`](.cursor/rules/issue-tracker.md) and [`spec/meta/github-issues.md`](spec/meta/github-issues.md).

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`.cursor/rules/triage-labels.md`](.cursor/rules/triage-labels.md).

### Domain docs

Single-context: `CONTEXT.md` + `spec/adr/`; MVP specs in `spec/`. See [`.cursor/rules/domain.md`](.cursor/rules/domain.md).
