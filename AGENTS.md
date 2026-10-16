# AGENTS.md

Instructions for AI agents working in the SmartWealthAI repository.

## Project phase

SmartWealthAI is a **portfolio monorepo** (investing + credit; fraud later). See [`CONTEXT-MAP.md`](CONTEXT-MAP.md).

| Domain | Status |
| --- | --- |
| **Investing** (Magic Formula demo) | **Delivered** (v0.1.0). Code under `investing/` (`investing/src/investing/`, `investing/CONTEXT.md`). Feature specs under [`specs/`](specs/README.md). |
| **Credit** (CSS) | **Active next.** Code under `credit/` (`credit/CONTEXT.md`, guides under `credit/docs/guides/`). Feature specs under [`specs/`](specs/README.md). |
| **Phase 2 Quantitative Value** | **Cancelled** for active execution ([ADR-0003](docs/adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`). |

Feature work must align with a Spec Kit spec under `specs/<###-slug>/` and domain constraints (`investing/CONTEXT.md` / `credit/CONTEXT.md`, frozen [`investing/docs/architecture/architecture.md`](investing/docs/architecture/architecture.md) for investing). See [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

Do not treat root `notebooks/` as canonical architecture. Domain code lives under `investing/src/investing/` and `credit/src/credit/`.

## Documentation map (source of truth)

| Path | Purpose |
| --- | --- |
| `specs/` | **Feature specs** (Spec Kit delivery: `spec.md`, plans/tasks when present) — index [`specs/README.md`](specs/README.md) |
| `.specify/` | Spec Kit tooling, constitution, assessments, bugs |
| `CONTEXT-MAP.md` | Portfolio domain map, relationships, delivery sequencing |
| `investing/CONTEXT.md` | Investing ubiquitous language |
| `credit/CONTEXT.md` | Credit / CSS ubiquitous language |
| `investing/README.md` | Investing domain entry (manager-facing) |
| `credit/README.md` | Credit domain entry (manager-facing) |
| `credit/docs/guides/` | Credit operator guides |
| `docs/adr/*.md` | Architecture Decision Records (hard-to-reverse choices) |
| `specs/006-june-demo-slice/spec.md` | Investing June 30 demo slice (delivered) |
| `investing/docs/architecture/architecture.md` | Investing MVP vision (frozen; see ADR-0003) |
| `investing/docs/requirements/requirements.md` | Sprint 0 spike (historical) |
| `investing/docs/backlog/backlog.md` | Informal ideas mapped to investing features |
| `docs/README.md` | Index of root `docs/` (ADRs) and pointers |

Former paths under `investing/docs/features/` and `credit/docs/features/` are redirect stubs only.

See also `.cursor/rules/*.mdc` for persistent agent guidance.

## Language

Write all code, comments, docstrings, documentation, commits, and PR text in **English**.

## Spec-driven workflow

1. **New features:** `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` (artifacts under `specs/<###-slug>/`). Optional assess first: `/speckit-assess-*` under `.specify/assessments/`.
2. **Existing features (Living Spec):** edit that folder’s `spec.md` in place; align plan/tasks when resuming delivery. Do not invent a new number unless scope is a new product slice.
3. Read domain constraints: investing → `investing/docs/architecture/architecture.md` + `investing/CONTEXT.md`; credit → `credit/CONTEXT.md` + `CONTEXT-MAP.md`.
4. Resolve open questions in the spec; record decisions in the spec or ADR.
5. Implement only what the spec allows for the current phase.
6. After implementation, update the owning `spec.md` (implementation status, acceptance criteria, links to code).
7. Small bugs / typos / CI one-liners: bug extension or lightweight path — not a full SDD loop.
8. **Credit mart schema changes:** if a stage creates, drops, or renames mart columns or changes grain (raw → application), do not rely on green tests alone — say the transform in the PR/agent summary, update the mart README sidecar + `credit/data/README.md` in the same change, and open/update a GitHub issue plus a line in [`specs/013-css-chapter5-mart-and-scoring/spec.md`](specs/013-css-chapter5-mart-and-scoring/spec.md) **before** merge.

## Runtime

- **Python:** 3.11+ (`requires-python = ">=3.11,<4.0"` in root `pyproject.toml`)
- **Dependencies:** uv workspace; members `credit` + `investing` with **lean per-domain deps** ([#183](https://github.com/JLaborda/SmartWealthAI/issues/183), [ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md)). Shared libs (`pandas`, `click`, `mlflow-skinny`) are listed in both members. CI and Make use `--frozen` so installs match `uv.lock`.

```bash
# Full monorepo (both domains)
uv sync --frozen --group dev   # or: make install
uv run pytest                  # or: make test / make lint

# One domain only (credit has no yfinance; investing has no xgboost)
uv sync --frozen --package credit --group dev      # or: make install-credit
uv sync --frozen --package investing --group dev   # or: make install-investing
make test-credit    # pytest credit/tests (keeps --package; bare uv run would re-sync both)
make test-investing # pytest investing/tests
# After a domain-only sync, use `uv run --no-sync …` or `uv run --package <domain> …`
# so a plain `uv run` does not reinstall the other member.
```

### MLflow (demo pipeline runs)

`mlflow-skinny` is a uv dependency (`uv sync` is enough for logging). No local MLflow UI server is required for #61.

```bash
# Usually do NOT export — code defaults to file://$(pwd)/mlruns.
# When you do export, expand pwd on the current machine (never hardcode /workspaces/...):
export MLFLOW_TRACKING_URI="file://$(pwd)/mlruns"
export MLFLOW_ALLOW_FILE_STORE=true   # required for file:// with MLflow 3.14+ (set automatically by score-universe)
```

Logged by `score-universe` after ranking/portfolio construction ([#61](https://github.com/JLaborda/SmartWealthAI/issues/61)). After switching Dev Container ↔ Mac host, if MLflow hits a read-only `/workspaces` path: first `unset MLFLOW_TRACKING_URI` (or set it to `file://$(pwd)/mlruns`), and confirm the tracking URI points at a writable path under the repo (or your intended store). Prefer correcting the URI over deleting. Only if local `mlruns/` is clearly corrupted or still points at an unusable absolute `/workspaces` artifact location — and you accept losing those local runs — then remove or recreate that directory.

To view runs on a remote tracking server (e.g. EC2 Docker), set `MLFLOW_TRACKING_URI` to that server **before** `score-universe` and use a shared artifact store (e.g. S3). Local `mlruns/` are not visible to a remote server unless you log there at run time.

### Fundamentals — demo path (SimFin)

Active pipeline for the June 30 demo slice. Requires `SIMFIN_API_KEY` (never commit).

**Local dev:** copy `.env.example` → `.env`, set the key, open a new terminal (devcontainer loads `.env` via `.devcontainer/install-env-hook.sh`). `.env` is gitignored.

**Cloud agents / CI:** do not rely on `.env` — inject `SIMFIN_API_KEY` via Cursor cloud agent secrets, GitHub Actions secrets (CI), or AWS Secrets Manager (runtime per architecture).

```bash
export SIMFIN_API_KEY="<from user secrets>"
uv run download-simfin
```

Spec: [`specs/001-etl-data-lake/spec.md`](specs/001-etl-data-lake/spec.md). Operator guide: [`investing/docs/guides/download-simfin.md`](investing/docs/guides/download-simfin.md). Delivery target: [`specs/006-june-demo-slice/spec.md`](specs/006-june-demo-slice/spec.md).

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

Git specs under `specs/` are canonical for features. Notion tracks execution tasks only. Setup: [`investing/docs/NOTION_SETUP.md`](investing/docs/NOTION_SETUP.md).

### Default task board

| Setting | Value |
| --- | --- |
| **Board name** | `Cursor Agent Tasks` |
| **Location** | This project's Notion workspace (connected via Cursor Notion MCP) |
| **Board URL in repo** | Not stored — use MCP OAuth and search by board name |

Agents must use the Notion MCP server (authenticated in **Cursor → Settings → MCP**) to find and update this board. Search the workspace for `Cursor Agent Tasks` before creating or editing tasks. Do not ask the user to commit a Notion URL to the repository.

Each task should reference a spec path (e.g. `specs/002-universe-construction/spec.md`) and copy acceptance criteria from that spec. When a task completes, update the Git spec first, then mark the Notion task done.

**Skills (after MCP auth):** `spec-to-implementation`, `create-task`, `tasks-build`, `tasks-explain-diff`. For `tasks-build`, the user supplies a single task URL in chat (not in this file).

**Commit workflow:** `/commit_split` — project skill [`.cursor/skills/commit-split/SKILL.md`](.cursor/skills/commit-split/SKILL.md); splits into conventional commits; out-of-scope paths follow [`.gitignore`](.gitignore).

## Agent skills

Matt Pocock engineering skills ([`mattpocock/skills`](https://github.com/mattpocock/skills)) are vendored under [`.cursor/skills/`](.cursor/skills/). They read repo-specific config from [`.cursor/rules/`](.cursor/rules/) (issue tracker, triage labels, domain layout).

### Issue tracker

GitHub Issues on `JLaborda/SmartWealthAI` via the `gh` CLI. Specs in Git remain canonical; Notion is optional for execution only. See [`.cursor/rules/issue-tracker.md`](.cursor/rules/issue-tracker.md).

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [`.cursor/rules/triage-labels.md`](.cursor/rules/triage-labels.md).

### Domain docs

Portfolio map: `CONTEXT-MAP.md`. Investing glossary: `investing/CONTEXT.md`. Credit glossary: `credit/CONTEXT.md`. Feature index: `specs/README.md`. ADRs in `docs/adr/`. See [`.cursor/rules/domain.md`](.cursor/rules/domain.md).
