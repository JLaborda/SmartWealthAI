# SmartWealthAI documentation

All MVP architecture and feature specifications live here. This tree is the **versioned source of truth** for the project. Notion is used only for task tracking (see [AGENTS.md](../AGENTS.md)).

## Ubiquitous language

Domain vocabulary lives in [`CONTEXT.md`](../CONTEXT.md) at the repo root (Matt Pocock [single-context](https://github.com/mattpocock/skills) pattern). Extend it with `/grill-with-docs`; agent consumption rules are in [`.cursor/rules/domain.md`](../.cursor/rules/domain.md).

## Layout

```text
docs/
  adr/                           # Architecture Decision Records (why, not how)
  mvp/
    demo-slice.md                # June 30 delivery target (narrow vertical)
    architecture/architecture.md # MVP vision, principles, module table, decisions
    features/                    # One spec per module
    guides/                      # Operator guides for implemented slices
    prds/                        # Implementation PRDs (tooling and cross-cutting)
    requirements/requirements.md  # Sprint 0 spike (historical; superseded by MVP specs)
    backlog/backlog.md           # Informal ideas mapped to features
```

## Architecture Decision Records (ADRs)

Short notes on hard-to-reverse choices. See [`docs/adr/`](../adr/).

| ADR | Decision |
| --- | --- |
| [0001](../adr/0001-simfin-fundamentals-mvp.md) | SimFin fundamentals for MVP; SEC ETL phase 2 |
| [0002](../adr/0002-june-demo-scope-cut.md) | June 30 demo slice scope cut |

## Demo slice

**Current delivery target:** [`demo-slice.md`](mvp/demo-slice.md) — SimFin → US universe → ROC/EY → top-30 portfolio → dashboard.

## Operator guides

| Guide | When to use |
| --- | --- |
| [download-simfin.md](mvp/guides/download-simfin.md) | **Active demo path:** download SimFin bulk fundamentals and `shareprices/latest`, then build universe and run-date price snapshots. |
| [download-fundamentals.md](mvp/guides/download-fundamentals.md) | **Frozen SEC spike** (phase 2): download `companyfacts` + `edgartools` for a universe. Active demo path uses SimFin — see [`demo-slice.md`](mvp/demo-slice.md) and [`etl-data-lake.md`](mvp/features/etl-data-lake.md). |

## PRDs

| PRD | Scope |
| --- | --- |
| [devcontainer/prd.md](mvp/prds/devcontainer/prd.md) | Reproducible dev environment (Cursor / EC2) |
| [ci-cd/ci-cd-prd.md](mvp/prds/ci-cd/ci-cd-prd.md) | Phase 0 CI/CD, AWS integration, ECS deploy path |

## Feature specs

| Spec | Module |
| --- | --- |
| [etl-data-lake.md](mvp/features/etl-data-lake.md) | ETL and data lake |
| [universe-construction.md](mvp/features/universe-construction.md) | Universe construction |
| [permanent-loss-filter.md](mvp/features/permanent-loss-filter.md) | Permanent loss filter |
| [high-quality-stocks.md](mvp/features/high-quality-stocks.md) | Quality scoring |
| [cheap-stocks.md](mvp/features/cheap-stocks.md) | Cheapness scoring |
| [corroborative-signals.md](mvp/features/corroborative-signals.md) | Corroborative signals |
| [unstructured-financial-data.md](mvp/features/unstructured-financial-data.md) | Unstructured data |
| [backtesting.md](mvp/features/backtesting.md) | Backtesting |
| [sell-watch.md](mvp/features/sell-watch.md) | Sell watch |
| [portfolio-evolution.md](mvp/features/portfolio-evolution.md) | Portfolio evolution (model vs personal vs benchmarks) |
| [dashboard-reporting.md](mvp/features/dashboard-reporting.md) | Dashboard and reporting |
| [broker-execution.md](mvp/features/broker-execution.md) | Broker execution (paper) |

Start with [architecture.md](mvp/architecture/architecture.md) for global constraints, then open the feature spec for the area you are changing.

## Spec-driven workflow

1. Read or update the relevant feature spec.
2. Align with architecture decisions (point-in-time data, exclusions, paper trading, etc.).
3. Implement only what the spec allows for the current phase.
4. Update the spec after implementation (status, acceptance criteria, code links).

## Notion tasks

- Duplicate the [Code with Notion board template](https://notion.notion.site/code-with-notion-board).
- Link each task to a spec path under `docs/mvp/features/`.
- Task board: **`Cursor Agent Tasks`** in Notion (MCP OAuth; see [NOTION_SETUP.md](mvp/NOTION_SETUP.md) and [AGENTS.md](../AGENTS.md)).

Cursor agent rules: `.cursor/rules/*.mdc`.
