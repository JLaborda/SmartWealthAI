# SmartWealthAI documentation

Portfolio monorepo: domain map and relationships live in [`CONTEXT-MAP.md`](../CONTEXT-MAP.md). This root `docs/` tree holds **cross-cutting ADRs**. **Feature specs** live under [`specs/`](../specs/README.md) (Spec Kit). Domain glossaries, architecture vision, and operator guides remain under `investing/docs/` and `credit/docs/`. Notion is used only for task tracking (see [AGENTS.md](../AGENTS.md)).

## Ubiquitous language

| Domain | Glossary |
| --- | --- |
| Portfolio / domains | [`CONTEXT-MAP.md`](../CONTEXT-MAP.md) |
| Investing | [`investing/CONTEXT.md`](../investing/CONTEXT.md) |
| Credit (CSS) | [`credit/CONTEXT.md`](../credit/CONTEXT.md) |

Extend glossaries with `/grill-with-docs`; agent consumption rules are in [`.cursor/rules/domain.md`](../.cursor/rules/domain.md).

## Layout

```text
specs/                           # Spec Kit feature delivery (canonical)
  README.md
  <###-slug>/spec.md

.specify/                        # Spec Kit tooling, constitution, assessments, bugs

docs/
  adr/                           # Architecture Decision Records (why, not how)

investing/docs/                  # Glossaries live in CONTEXT; here: architecture, guides, historical
  architecture/architecture.md
  guides/
  prds/
  requirements/
  backlog/
  features/                      # redirect stubs → specs/

credit/docs/                     # Guides + feature redirect stubs → specs/
  guides/
  features/
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
| [0005](adr/0005-poetry-to-uv-workspace.md) | Primary tooling Poetry → uv workspace |

## Investing entry points

| Doc | Role |
| --- | --- |
| [june-demo-slice](../specs/006-june-demo-slice/spec.md) | June 30 delivery (delivered) |
| [architecture.md](../investing/docs/architecture/architecture.md) | Frozen historical vision (ADR-0003) |
| [phase2/prd.md](../investing/docs/prds/phase2/prd.md) | **Cancelled** — QV funnel ([ADR-0003](adr/0003-phase2-qv-cancelled.md)) |

## Notion

Link each task to a Spec Kit path under `specs/<###-slug>/spec.md`.
