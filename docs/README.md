# SmartWealthAI documentation

Portfolio monorepo: domain map and relationships live in [`CONTEXT-MAP.md`](../CONTEXT-MAP.md). This root `docs/` tree holds **cross-cutting ADRs**. Investing specs live under [`investing/docs/`](../investing/docs/); credit specs under [`credit/docs/`](../credit/docs/). Notion is used only for task tracking (see [AGENTS.md](../AGENTS.md)).

## Ubiquitous language

| Domain | Glossary |
| --- | --- |
| Portfolio / domains | [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) |
| Investing | [`investing/CONTEXT.md`](../investing/CONTEXT.md) |
| Credit (CSS) | [`credit/CONTEXT.md`](../credit/CONTEXT.md) |

Extend glossaries with `/grill-with-docs`; agent consumption rules are in [`.cursor/rules/domain.md`](../.cursor/rules/domain.md).

## Layout

```text
docs/
  adr/                           # Architecture Decision Records (why, not how)

investing/docs/                  # Investing Magic Formula specs (moved from docs/mvp/)
  demo-slice.md
  architecture/architecture.md
  features/
  guides/
  prds/
  requirements/
  backlog/

credit/docs/                     # Credit / CSS feature specs
```

Domain READMEs: [`investing/`](../investing/), [`credit/`](../credit/).

## Architecture Decision Records (ADRs)

Short notes on hard-to-reverse choices. See [`docs/adr/`](adr/).

| ADR | Decision |
| --- | --- |
| [0001](adr/0001-simfin-fundamentals-mvp.md) | SimFin fundamentals for MVP; SEC ETL deferred |
| [0002](adr/0002-june-demo-scope-cut.md) | June 30 demo slice scope cut |
| [0003](adr/0003-phase2-qv-cancelled.md) | Phase 2 Quantitative Value cancelled for active execution |
| [0004](adr/0004-platform-ephemeral-fargate-serve.md) | Ephemeral Fargate CSS serve demo |

## Investing entry points

| Doc | Role |
| --- | --- |
| [demo-slice.md](../investing/docs/demo-slice.md) | June 30 delivery (delivered) |
| [architecture.md](../investing/docs/architecture/architecture.md) | Frozen historical vision (ADR-0003) |
| [phase2/prd.md](../investing/docs/prds/phase2/prd.md) | **Cancelled** — QV funnel ([ADR-0003](adr/0003-phase2-qv-cancelled.md)) |

## Notion

Link each task to a spec path under `investing/docs/features/` or `credit/docs/`.
