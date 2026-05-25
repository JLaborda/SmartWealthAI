# AGENTS.md

Instructions for AI agents working in the SmartWealthAI repository.

## Project phase

SmartWealthAI is in **MVP planning and spec refinement**. Architecture and features are defined in Markdown under `docs/mvp/`. Implementation work must align with a feature spec in `docs/mvp/features/` and respect cross-cutting rules in `docs/mvp/architecture/architecture.md`.

Do not treat `src/` or `notebooks/` as canonical architecture; they are legacy exploration and out of scope for planning context.

## Documentation map (source of truth)

| Path | Purpose |
| --- | --- |
| `CONTEXT.md` | Ubiquitous language (domain terms; extend via `/grill-with-docs`) |
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

- **Python:** 3.13+ (`requires-python = "^3.13"` in `pyproject.toml`)
- **Dependencies:** Poetry

```bash
poetry env use python3.13
poetry install          # use `poetry install --no-root` if install fails without a package layout
poetry run python <script.py>
```

No test suite or linter is configured yet unless added explicitly.

## Gotchas

- `yfinance` and other data providers need network access.
- Local/generated data under `data/clean/`, `data/raw/`, `data/cache/`, `data/local/`, and `data/tmp/` is gitignored. Never commit personal finance files or raw broker exports.
- Small canonical reference inputs under `data/reference/` are versioned for reproducible universe construction, backtesting, ticker mapping, and delisting handling.

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

**Commit workflow:** `/commit_split` — split changes into conventional commits; respects [`.commit-split-ignore`](.commit-split-ignore). See [`docs/agents/commit-split.md`](docs/agents/commit-split.md).

## Agent skills

Matt Pocock engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) read repo-specific config from `docs/agents/`. Installed globally under `~/.agents/skills/`.

### Issue tracker

GitHub Issues on `JLaborda/SmartWealthAI` via the `gh` CLI. MVP specs in `docs/mvp/` remain canonical; Notion is optional for execution only. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at repo root; MVP specs in `docs/mvp/` during planning. See `docs/agents/domain.md`.
