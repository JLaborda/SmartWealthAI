---
description: How agents consume CONTEXT.md, ADRs, and MVP specs (Matt Pocock skills)
alwaysApply: false
---

# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

**Single-context** — ubiquitous language in `CONTEXT.md` at the repo root plus system-wide ADRs.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root (ubiquitous language; created or extended by `/grill-with-docs` when terms are resolved).
- **`spec/adr/`** — architectural decision records for cross-cutting choices.
- **`spec/constitution/mission.md`** — MVP vision, closed decisions, and module map (canonical during spec-driven phase).
- **Relevant `spec/features/00N-slug/spec.md`** — feature scope and acceptance criteria for the area you are changing.

If `CONTEXT.md` or `spec/adr/` do not exist yet, **proceed silently**. Do not flag their absence or suggest creating them upfront. Use `spec/` as the source of truth until `/grill-with-docs` materializes terms into `CONTEXT.md`.

Do not treat `src/` or `notebooks/` as canonical architecture; they are legacy exploration per `AGENTS.md`.

## File structure

```
/
├── CONTEXT.md                 ← ubiquitous language (extend via grill-with-docs)
├── spec/
│   ├── constitution/          ← mission, tech-stack, roadmap
│   ├── features/              ← 00N-slug/spec.md (+ plan.md, tasks.md)
│   └── adr/
└── src/                       ← implementation (not planning truth)
```

## Use CONTEXT vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), prefer terms from `CONTEXT.md` when defined there; otherwise use terms consistently with `spec/` (e.g. point-in-time, universe, EY rank, Magic Formula replica).

If the concept you need isn't in `CONTEXT.md` yet, either reconsider invented language or note the gap for `/grill-with-docs`.

## Flag ADR conflicts

If your output contradicts an existing ADR or a **closed decision** in `spec/constitution/mission.md`, surface it explicitly rather than silently overriding:

> _Contradicts [decision or ADR] — but worth reopening because…_

Update the architecture doc or ADR before implementing a conflicting change.
