# SmartWealthAI documentation

Portfolio monorepo: domain map and relationships live in [`CONTEXT-MAP.md`](../CONTEXT-MAP.md). This `docs/` tree is the **versioned source of truth for investing (Magic Formula demo)** ADRs, architecture, and feature specs. Credit specs live under [`credit/docs/`](../credit/docs/), not here. Notion is used only for task tracking (see [AGENTS.md](../AGENTS.md)).

## Ubiquitous language

| Domain | Glossary |
| --- | --- |
| Portfolio / domains | [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) |
| Investing | [`CONTEXT.md`](../CONTEXT.md) (until moved to `investing/CONTEXT.md`) |
| Credit (CSS) | [`credit/CONTEXT.md`](../credit/CONTEXT.md) |

Extend glossaries with `/grill-with-docs`; agent consumption rules are in [`.cursor/rules/domain.md`](../.cursor/rules/domain.md).

## Layout

```text
docs/
  adr/                           # Architecture Decision Records (why, not how)
  mvp/
    demo-slice.md                # Investing June 30 demo (delivered)
    architecture/architecture.md # Investing MVP vision (frozen; ADR-0003)
    features/                    # Investing module specs
    guides/                      # Operator guides for investing slices
    prds/                        # PRDs (Phase 2 QV PRD cancelled — ADR-0003)
    requirements/requirements.md  # Sprint 0 spike (historical)
    backlog/backlog.md           # Informal ideas mapped to investing features
```

Credit feature specs (when present): `credit/docs/`. Domain READMEs: [`investing/`](../investing/), [`credit/`](../credit/).

## Architecture Decision Records (ADRs)

Short notes on hard-to-reverse choices. See [`docs/adr/`](adr/).

| ADR | Decision |
| --- | --- |
| [0001](adr/0001-simfin-fundamentals-mvp.md) | SimFin fundamentals for MVP; SEC ETL deferred |
| [0002](adr/0002-june-demo-scope-cut.md) | June 30 demo slice scope cut |
| [0003](adr/0003-phase2-qv-cancelled.md) | Phase 2 Quantitative Value cancelled for active execution |

## Demo slice (investing)

**Delivered:** [`demo-slice.md`](mvp/demo-slice.md) — SimFin → US universe → ROC/EY → top-30 portfolio → dashboard.

## Operator guides

| Guide | When to use |
| --- | --- |
| [download-simfin.md](mvp/guides/download-simfin.md) | **Active investing demo path:** download SimFin bulk fundamentals and `shareprices/latest`, then build universe and run-date price snapshots. |
| [download-fundamentals.md](mvp/guides/download-fundamentals.md) | **Frozen SEC spike:** download `companyfacts` + `edgartools` for a universe. Active demo path uses SimFin — see [`demo-slice.md`](mvp/demo-slice.md) and [`etl-data-lake.md`](mvp/features/etl-data-lake.md). |

## PRDs

| PRD | Scope |
| --- | --- |
| [devcontainer/prd.md](mvp/prds/devcontainer/prd.md) | Reproducible dev environment (Cursor / EC2) |
| [ci-cd/ci-cd-prd.md](mvp/prds/ci-cd/ci-cd-prd.md) | Phase 0 CI/CD, AWS integration, ECS deploy path |
| [phase2/prd.md](mvp/prds/phase2/prd.md) | **Cancelled** — Quantitative Value funnel, cloud, backtest, sell-watch ([ADR-0003](adr/0003-phase2-qv-cancelled.md); branch `archive/phase2-qv`) |

## Feature specs (investing)

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

Start with [architecture.md](mvp/architecture/architecture.md) for investing constraints (frozen vision), then open the feature spec for the area you are changing. For credit work, use [`credit/docs/`](../credit/docs/) and [`credit/CONTEXT.md`](../credit/CONTEXT.md).

## Spec-driven workflow

1. Read or update the relevant feature spec (investing: here; credit: `credit/docs/`).
2. Align with architecture decisions and ADRs.
3. Implement only what the spec allows for the current phase.
4. Update the spec after implementation (status, acceptance criteria, code links).

## Notion tasks

- Duplicate the [Code with Notion board template](https://notion.notion.site/code-with-notion-board).
- Link each task to a spec path under `docs/mvp/features/` or `credit/docs/`.
- Task board: **`Cursor Agent Tasks`** in Notion (MCP OAuth; see [NOTION_SETUP.md](mvp/NOTION_SETUP.md) and [AGENTS.md](../AGENTS.md)).

Cursor agent rules: `.cursor/rules/*.mdc`.
