# AGENTS.md

Instructions for AI agents working in the SmartWealthAI repository.

## Project phase

SmartWealthAI is in **MVP planning and spec refinement**, with a **June 30, 2026 demo slice** as the current delivery target. Architecture and features are defined in Markdown under `docs/mvp/`. Implementation work must align with a feature spec in `docs/mvp/features/` and respect cross-cutting rules in `docs/mvp/architecture/architecture.md`.

Do not treat `src/` or `notebooks/` as canonical architecture; they are legacy exploration and out of scope for planning context.

## Documentation map (source of truth)

| Path | Purpose |
| --- | --- |
| `CONTEXT.md` | Ubiquitous language (domain terms; extend via `/grill-with-docs`) |
| `docs/adr/*.md` | Architecture Decision Records (hard-to-reverse choices) |
| `docs/mvp/demo-slice.md` | June 30 delivery target (narrow vertical slice) |
| `docs/mvp/architecture/architecture.md` | MVP vision, principles, module table, closed decisions |
| `docs/mvp/features/*.md` | Per-module specs (scope, acceptance criteria, diagrams) |
| `docs/mvp/requirements/requirements.md` | Sprint 0 spike (superseded by MVP specs; historical reference) |
| `docs/mvp/backlog/backlog.md` | Informal product ideas mapped to MVP features |
| `docs/README.md` | Index of the docs tree |

See also `.cursor/rules/*.mdc` for persistent agent guidance.

## Language

Write all code, comments, docstrings, documentation, commits, and PR text in **English**.

## Spec-driven workflow

1. Identify the feature spec (e.g. `docs/mvp/features/cheap-stocks.md`).
2. Read `docs/mvp/architecture/architecture.md` for constraints (point-in-time data, exclusions, MLflow, paper trading, etc.).
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

### Fundamentals — demo path (SimFin)

Active pipeline for the June 30 demo slice. Requires `SIMFIN_API_KEY` (never commit).

```bash
export SIMFIN_API_KEY="<from user secrets>"
# SimFin connector CLI — to be added; see docs/mvp/demo-slice.md
```

Spec: [`docs/mvp/features/etl-data-lake.md`](docs/mvp/features/etl-data-lake.md). Delivery target: [`docs/mvp/demo-slice.md`](docs/mvp/demo-slice.md).

### Fundamentals — SEC spike (frozen, phase 2)

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

Git specs in `docs/mvp/` are canonical. Notion tracks execution tasks only. Setup: [`docs/mvp/NOTION_SETUP.md`](docs/mvp/NOTION_SETUP.md).

### Default task board

| Setting | Value |
| --- | --- |
| **Board name** | `Cursor Agent Tasks` |
| **Location** | This project's Notion workspace (connected via Cursor Notion MCP) |
| **Board URL in repo** | Not stored — use MCP OAuth and search by board name |

Agents must use the Notion MCP server (authenticated in **Cursor → Settings → MCP**) to find and update this board. Search the workspace for `Cursor Agent Tasks` before creating or editing tasks. Do not ask the user to commit a Notion URL to the repository.

Each task should reference a spec path (e.g. `docs/mvp/features/universe-construction.md`) and copy acceptance criteria from that spec. When a task completes, update the Git spec first, then mark the Notion task done.

**Skills (after MCP auth):** `spec-to-implementation`, `create-task`, `tasks-build`, `tasks-explain-diff`. For `tasks-build`, the user supplies a single task URL in chat (not in this file).

**Commit workflow:** `/commit_split` — project skill [`.cursor/skills/commit-split/SKILL.md`](.cursor/skills/commit-split/SKILL.md); splits into conventional commits; out-of-scope paths follow [`.gitignore`](.gitignore).

## Agent skills

Matt Pocock engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) are vendored under [`.cursor/skills/`](.cursor/skills/). They read repo-specific config from [`.cursor/rules/`](.cursor/rules/) (issue tracker, triage labels, domain layout).

### Issue tracker

GitHub Issues on `JLaborda/SmartWealthAI` via the `gh` CLI. MVP specs in `docs/mvp/` remain canonical; Notion is optional for execution only. See [`.cursor/rules/issue-tracker.md`](.cursor/rules/issue-tracker.md).

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`.cursor/rules/triage-labels.md`](.cursor/rules/triage-labels.md).

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at repo root; MVP specs in `docs/mvp/` during planning. See [`.cursor/rules/domain.md`](.cursor/rules/domain.md).
