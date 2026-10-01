# AGENTS.md

Instructions for AI agents working in the SmartWealthAI repository.

## Project phase

SmartWealthAI is a **portfolio monorepo** (investing + credit; fraud later). See [`CONTEXT-MAP.md`](CONTEXT-MAP.md).

| Domain | Status |
| --- | --- |
| **Investing** (Magic Formula demo) | **Delivered** (v0.1.0). Specs under `docs/mvp/`; code still under `src/smartwealthai` until a migrate-only PR. |
| **Credit** (CSS) | **Active next.** Specs and new code under `credit/` (`credit/docs/`, `credit/CONTEXT.md`). |
| **Phase 2 Quantitative Value** | **Cancelled** for active execution ([ADR-0003](docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`). |

Investing changes must align with a feature spec in `docs/mvp/features/` and [`docs/mvp/architecture/architecture.md`](docs/mvp/architecture/architecture.md) (frozen historical vision — not a live QV north star). Credit changes align with specs under `credit/docs/`.

Do not treat `src/` or `notebooks/` as canonical architecture for new domains; investing code there is the demo delivery, not a template to copy for credit.

## Documentation map (source of truth)

| Path | Purpose |
| --- | --- |
| `CONTEXT-MAP.md` | Portfolio domain map, relationships, delivery sequencing |
| `CONTEXT.md` | Investing ubiquitous language (until moved to `investing/CONTEXT.md`) |
| `credit/CONTEXT.md` | Credit / CSS ubiquitous language |
| `investing/README.md` | Investing domain entry (manager-facing) |
| `credit/README.md` | Credit domain entry (manager-facing) |
| `credit/docs/` | Credit feature specs (when present) |
| `docs/adr/*.md` | Architecture Decision Records (hard-to-reverse choices) |
| `docs/mvp/demo-slice.md` | Investing June 30 demo slice (delivered) |
| `docs/mvp/architecture/architecture.md` | Investing MVP vision (frozen; see ADR-0003) |
| `docs/mvp/features/*.md` | Investing per-module specs |
| `docs/mvp/requirements/requirements.md` | Sprint 0 spike (historical) |
| `docs/mvp/backlog/backlog.md` | Informal ideas mapped to investing features |
| `docs/README.md` | Index of the `docs/` tree |

See also `.cursor/rules/*.mdc` for persistent agent guidance.

## Language

Write all code, comments, docstrings, documentation, commits, and PR text in **English**.

## Spec-driven workflow

1. Identify the feature spec: investing → `docs/mvp/features/<feature>.md`; credit → `credit/docs/` (when present).
2. Read the matching architecture/context: investing → `docs/mvp/architecture/architecture.md` + `CONTEXT.md`; credit → `credit/CONTEXT.md` + `CONTEXT-MAP.md`.
3. Resolve open questions in the spec; record decisions in the spec or ADR.
4. Implement only what the spec allows for the current phase.
5. After implementation, update the feature spec (implementation status, acceptance criteria, links to code when it exists).
6. **Credit mart schema changes:** if a stage creates, drops, or renames mart columns or changes grain (raw → application), do not rely on green tests alone — say the transform in the PR/agent summary, update the mart README sidecar + `credit/data/README.md` in the same change, and open/update a GitHub issue plus a line in the credit feature spec **before** merge. See [`credit/docs/features/css-chapter5-mart-and-scoring.md`](credit/docs/features/css-chapter5-mart-and-scoring.md).

## Runtime

- **Python:** 3.11+ (`requires-python = "^3.11"` in `pyproject.toml`)
- **Dependencies:** Poetry

```bash
poetry env use python3.11
poetry install
poetry run pytest
```

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

Spec: [`docs/mvp/features/etl-data-lake.md`](docs/mvp/features/etl-data-lake.md). Operator guide: [`docs/mvp/guides/download-simfin.md`](docs/mvp/guides/download-simfin.md). Delivery target: [`docs/mvp/demo-slice.md`](docs/mvp/demo-slice.md).

### Fundamentals — SEC spike (frozen)

```bash
export SEC_IDENTITY="Your Name your@email.com"
poetry run download-fundamentals --universe dow30
```

Guide: [`docs/mvp/guides/download-fundamentals.md`](docs/mvp/guides/download-fundamentals.md).

## Gotchas

- `yfinance`, SimFin bulk API, and other data providers need network access.
- SimFin requires `SIMFIN_API_KEY` in the environment (AWS Secrets Manager at runtime).
- SEC EDGAR and `edgartools` require `SEC_IDENTITY` (real name + email) for the **frozen** SEC spike only.
- `data/` is gitignored except `data/reference/**` (versioned universe and mapping CSVs).
  Never commit personal finance files or raw broker exports.

## Notion (task tracking)

Git specs are canonical (`docs/mvp/` for investing; `credit/docs/` for credit). Notion tracks execution tasks only. Setup: [`docs/mvp/NOTION_SETUP.md`](docs/mvp/NOTION_SETUP.md).

### Default task board

| Setting | Value |
| --- | --- |
| **Board name** | `Cursor Agent Tasks` |
| **Location** | This project's Notion workspace (connected via Cursor Notion MCP) |
| **Board URL in repo** | Not stored — use MCP OAuth and search by board name |

Agents must use the Notion MCP server (authenticated in **Cursor → Settings → MCP**) to find and update this board. Search the workspace for `Cursor Agent Tasks` before creating or editing tasks. Do not ask the user to commit a Notion URL to the repository.

Each task should reference a spec path (e.g. `docs/mvp/features/universe-construction.md` or `credit/docs/…`) and copy acceptance criteria from that spec. When a task completes, update the Git spec first, then mark the Notion task done.

**Skills (after MCP auth):** `spec-to-implementation`, `create-task`, `tasks-build`, `tasks-explain-diff`. For `tasks-build`, the user supplies a single task URL in chat (not in this file).

**Commit workflow:** `/commit_split` — project skill [`.cursor/skills/commit-split/SKILL.md`](.cursor/skills/commit-split/SKILL.md); splits into conventional commits; out-of-scope paths follow [`.gitignore`](.gitignore).

## Agent skills

Matt Pocock engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) are vendored under [`.cursor/skills/`](.cursor/skills/). They read repo-specific config from [`.cursor/rules/`](.cursor/rules/) (issue tracker, triage labels, domain layout).

### Issue tracker

GitHub Issues on `JLaborda/SmartWealthAI` via the `gh` CLI. Specs in Git remain canonical; Notion is optional for execution only. See [`.cursor/rules/issue-tracker.md`](.cursor/rules/issue-tracker.md).

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`.cursor/rules/triage-labels.md`](.cursor/rules/triage-labels.md).

### Domain docs

Portfolio map: `CONTEXT-MAP.md`. Investing glossary: `CONTEXT.md`. Credit glossary: `credit/CONTEXT.md`. ADRs in `docs/adr/`. See [`.cursor/rules/domain.md`](.cursor/rules/domain.md).
