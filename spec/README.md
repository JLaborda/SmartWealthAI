# SmartWealthAI specifications

All MVP architecture and feature specifications live here. This tree is the **versioned source of truth** for the project. GitHub Issues track execution (see [`meta/github-issues.md`](meta/github-issues.md)).

## Ubiquitous language

Domain vocabulary lives in [`CONTEXT.md`](../CONTEXT.md) at the repo root. Extend it with `/grill-with-docs`; agent consumption rules are in [`.cursor/rules/domain.md`](../.cursor/rules/domain.md).

## Layout

```text
spec/
  README.md
  constitution/
    mission.md          # Vision, principles, module map, closed domain decisions
    tech-stack.md       # Technologies, infrastructure, runtime conventions
    roadmap.md          # Delivery phases, demo slice, feature priority
  features/
    00N-slug/
      spec.md           # Scope and acceptance criteria (always)
      plan.md           # Implementation plan (when in progress)
      tasks.md          # Versioned checklist (when in progress)
  adr/                  # Architecture Decision Records
  guides/               # Operator guides for implemented slices
  prds/                 # Tooling and cross-cutting PRDs
  meta/                 # Agent workflow conventions
  backlog/              # Informal product ideas
  archive/              # Superseded historical specs
```

## Constitution

| Document | Purpose |
| --- | --- |
| [`mission.md`](constitution/mission.md) | What we build, for whom, principles, module map |
| [`tech-stack.md`](constitution/tech-stack.md) | Python, AWS, SimFin, MLflow, CI/CD |
| [`roadmap.md`](constitution/roadmap.md) | June 30 demo slice, phase 2 order, feature registry |

## Architecture Decision Records

| ADR | Decision |
| --- | --- |
| [0001](adr/0001-simfin-fundamentals-mvp.md) | SimFin fundamentals for MVP; SEC ETL phase 2 |
| [0002](adr/0002-june-demo-scope-cut.md) | June 30 demo slice scope cut |
| [0003](adr/0003-terraform-for-aws-iac.md) | Terraform for AWS infrastructure (M2) |

## PRDs

| PRD | Scope |
| --- | --- |
| [devcontainer/prd.md](prds/devcontainer/prd.md) | Reproducible dev environment (Cursor / EC2) |
| [ci-cd/ci-cd-prd.md](prds/ci-cd/ci-cd-prd.md) | Phase 0 CI/CD, AWS integration, ECS deploy path |
| [terraform/terraform-prd.md](prds/terraform/terraform-prd.md) | M2 Terraform: S3, OIDC, Secrets Manager |
| [phase2/prd.md](prds/phase2/prd.md) | Phase 2: Quantitative Value, cloud, backtest, sell-watch |

## Operator guides

| Guide | When to use |
| --- | --- |
| [download-simfin.md](guides/download-simfin.md) | **Active demo path:** SimFin bulk fundamentals and prices |
| [download-fundamentals.md](guides/download-fundamentals.md) | **Frozen SEC spike** (phase 2) |

## Feature specs

| ID | Module | Spec |
| --- | --- | --- |
| 001 | Backtesting | [spec.md](features/001-backtesting/spec.md) |
| 002 | Broker execution | [spec.md](features/002-broker-execution/spec.md) |
| 003 | Cheap stocks | [spec.md](features/003-cheap-stocks/spec.md) |
| 004 | Corroborative signals | [spec.md](features/004-corroborative-signals/spec.md) |
| 005 | Dashboard reporting | [spec.md](features/005-dashboard-reporting/spec.md) |
| 006 | ETL + data lake | [spec.md](features/006-etl-data-lake/spec.md) |
| 007 | High-quality stocks | [spec.md](features/007-high-quality-stocks/spec.md) |
| 008 | Permanent loss filter | [spec.md](features/008-permanent-loss-filter/spec.md) |
| 009 | Portfolio evolution | [spec.md](features/009-portfolio-evolution/spec.md) |
| 010 | Sell-watch | [spec.md](features/010-sell-watch/spec.md) |
| 011 | Universe construction | [spec.md](features/011-universe-construction/spec.md) |
| 012 | Unstructured financial data | [spec.md](features/012-unstructured-financial-data/spec.md) |
| 013 | Quantitative Value | [spec.md](features/013-quantitative-value/spec.md) |
| 014 | CI/CD infrastructure | [spec.md](features/014-cicd-infrastructure/spec.md) |

Start with [`constitution/mission.md`](constitution/mission.md) for global constraints, then open the feature spec for the area you are changing.

## Spec-driven workflow

1. Read or update the relevant feature `spec.md`.
2. Align with [`constitution/mission.md`](constitution/mission.md) (point-in-time data, exclusions, paper trading, etc.).
3. When implementation starts, add `plan.md` and `tasks.md` under the feature folder.
4. Open **one GitHub issue per feature** (see [`meta/github-issues.md`](meta/github-issues.md)).
5. Update the spec after implementation (status, acceptance criteria, code links).

## New feature specs

Copy [`meta/feature-spec-template.md`](meta/feature-spec-template.md) into `spec/features/00N-slug/spec.md`. Register the ID in [`constitution/roadmap.md`](constitution/roadmap.md).
