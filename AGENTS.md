# AGENTS.md

Instructions for AI agents working in the SmartWealthAI repository.

## Project phase

SmartWealthAI is a **portfolio monorepo** (investing + credit; fraud later). See [`CONTEXT-MAP.md`](CONTEXT-MAP.md).

| Domain | Status |
| --- | --- |
| **Investing** (Magic Formula demo) | **Delivered** (v0.1.0). Code and specs under `investing/` (`investing/src/investing/`, `investing/docs/`, `investing/CONTEXT.md`). |
| **Credit** (CSS) | **Active next.** Specs and new code under `credit/` (`credit/docs/`, `credit/CONTEXT.md`). |
| **Phase 2 Quantitative Value** | **Cancelled** for active execution ([ADR-0003](docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`). |

Investing changes must align with a feature spec in `investing/docs/features/` and [`investing/docs/architecture/architecture.md`](investing/docs/architecture/architecture.md) (frozen historical vision — not a live QV north star). Credit changes align with specs under `credit/docs/`.

Do not treat root `notebooks/` as canonical architecture. Domain code lives under `investing/src/investing/` and `credit/src/credit/`.

## Documentation map (source of truth)

| Path | Purpose |
| --- | --- |
| `CONTEXT-MAP.md` | Portfolio domain map, relationships, delivery sequencing |
| `investing/CONTEXT.md` | Investing ubiquitous language |
| `credit/CONTEXT.md` | Credit / CSS ubiquitous language |
| `investing/README.md` | Investing domain entry (manager-facing) |
| `credit/README.md` | Credit domain entry (manager-facing) |
| `credit/docs/` | Credit feature specs (when present) |
| `docs/adr/*.md` | Architecture Decision Records (hard-to-reverse choices) |
| `investing/docs/demo-slice.md` | Investing June 30 demo slice (delivered) |
| `investing/docs/architecture/architecture.md` | Investing MVP vision (frozen; see ADR-0003) |
| `investing/docs/features/*.md` | Investing per-module specs |
| `investing/docs/requirements/requirements.md` | Sprint 0 spike (historical) |
| `investing/docs/backlog/backlog.md` | Informal ideas mapped to investing features |
| `docs/README.md` | Index of root `docs/` (ADRs) and pointers to domain docs |

See also `.cursor/rules/*.mdc` for persistent agent guidance.

## Language

Write all code, comments, docstrings, documentation, commits, and PR text in **English**.

## Spec-driven workflow

1. Identify the feature spec: investing → `investing/docs/features/<feature>.md`; credit → `credit/docs/` (when present).
2. Read the matching architecture/context: investing → `investing/docs/architecture/architecture.md` + `investing/CONTEXT.md`; credit → `credit/CONTEXT.md` + `CONTEXT-MAP.md`.
3. Resolve open questions in the spec; record decisions in the spec or ADR.
4. Implement only what the spec allows for the current phase.
5. After implementation, update the feature spec (implementation status, acceptance criteria, links to code when it exists).
6. **Credit mart schema changes:** if a stage creates, drops, or renames mart columns or changes grain (raw → application), do not rely on green tests alone — say the transform in the PR/agent summary, update the mart README sidecar + `credit/data/README.md` in the same change, and open/update a GitHub issue plus a line in the credit feature spec **before** merge. See [`credit/docs/features/css-chapter5-mart-and-scoring.md`](credit/docs/features/css-chapter5-mart-and-scoring.md).

## Runtime

- **Python:** 3.11+ (`requires-python = ">=3.11,<4.0"` in root `pyproject.toml`)
- **Dependencies:** uv workspace (`uv sync --group dev` / `make install`); members `credit` + `investing` ([ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md))

```bash
uv sync --group dev
uv run pytest
```

### MLflow (demo pipeline runs)

`mlflow-skinny` is a uv dependency (`uv sync` is enough for logging). No local MLflow UI server is required for #61.

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
uv run download-simfin
```

Spec: [`investing/docs/features/etl-data-lake.md`](investing/docs/features/etl-data-lake.md). Operator guide: [`investing/docs/guides/download-simfin.md`](investing/docs/guides/download-simfin.md). Delivery target: [`investing/docs/demo-slice.md`](investing/docs/demo-slice.md).

### Fundamentals — SEC spike (frozen)

```bash
export SEC_IDENTITY="Your Name your@email.com"
uv run download-fundamentals --universe dow30
```

Guide: [`investing/docs/guides/download-fundamentals.md`](investing/docs/guides/download-fundamentals.md).

## Gotchas

- `yfinance`, SimFin bulk API, and other data providers need network access.
- SimFin requires `SIMFIN_API_KEY` in the environment (AWS Secrets Manager at runtime).
- SEC EDGAR and `edgartools` require `SEC_IDENTITY` (real name + email) for the **frozen** SEC spike only.
- `data/` is gitignored except `data/reference/**` (versioned universe and mapping CSVs).
  Never commit personal finance files or raw broker exports.

## Notion (task tracking)

Git specs are canonical (`investing/docs/` for investing; `credit/docs/` for credit). Notion tracks execution tasks only. Setup: [`investing/docs/NOTION_SETUP.md`](investing/docs/NOTION_SETUP.md).

### Default task board

| Setting | Value |
| --- | --- |
| **Board name** | `Cursor Agent Tasks` |
| **Location** | This project's Notion workspace (connected via Cursor Notion MCP) |
| **Board URL in repo** | Not stored — use MCP OAuth and search by board name |

Agents must use the Notion MCP server (authenticated in **Cursor → Settings → MCP**) to find and update this board. Search the workspace for `Cursor Agent Tasks` before creating or editing tasks. Do not ask the user to commit a Notion URL to the repository.

Each task should reference a spec path (e.g. `investing/docs/features/universe-construction.md` or `credit/docs/…`) and copy acceptance criteria from that spec. When a task completes, update the Git spec first, then mark the Notion task done.

**Skills (after MCP auth):** `spec-to-implementation`, `create-task`, `tasks-build`, `tasks-explain-diff`. For `tasks-build`, the user supplies a single task URL in chat (not in this file).

**Commit workflow:** `/commit_split` — project skill [`.cursor/skills/commit-split/SKILL.md`](.cursor/skills/commit-split/SKILL.md); splits into conventional commits; out-of-scope paths follow [`.gitignore`](.gitignore).

## Agent skills

Matt Pocock engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) are vendored under [`.cursor/skills/`](.cursor/skills/). They read repo-specific config from [`.cursor/rules/`](.cursor/rules/) (issue tracker, triage labels, domain layout).

### Issue tracker

GitHub Issues on `JLaborda/SmartWealthAI` via the `gh` CLI. Specs in Git remain canonical; Notion is optional for execution only. See [`.cursor/rules/issue-tracker.md`](.cursor/rules/issue-tracker.md).

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`.cursor/rules/triage-labels.md`](.cursor/rules/triage-labels.md).

### Domain docs

Portfolio map: `CONTEXT-MAP.md`. Investing glossary: `investing/CONTEXT.md`. Credit glossary: `credit/CONTEXT.md`. ADRs in `docs/adr/`. See [`.cursor/rules/domain.md`](.cursor/rules/domain.md).
