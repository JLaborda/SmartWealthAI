---
description: How agents consume CONTEXT-MAP, domain CONTEXT files, ADRs, and specs (Matt Pocock skills)
alwaysApply: false
---

# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

**Portfolio (multi-context)** — domain map in `CONTEXT-MAP.md`; one ubiquitous-language file per domain; system-wide ADRs in `docs/adr/`.

## Before exploring, read these

- **`CONTEXT-MAP.md`** — domains, relationships, delivery sequencing, Sources.
- **Domain glossary** — investing: `CONTEXT.md`; credit: `credit/CONTEXT.md`.
- **`docs/adr/`** — architectural decision records for cross-cutting choices (including ADR-0003 Phase 2 QV cancelled).
- **Investing:** `docs/mvp/architecture/architecture.md` (frozen historical vision) and `docs/mvp/features/<feature>.md` when changing investing.
- **Credit:** `credit/docs/` feature specs when present; `credit/README.md` for domain entry.

If a CONTEXT file or `docs/adr/` does not exist yet, **proceed silently**. Do not flag their absence or suggest creating them upfront.

Do not treat `src/` or `notebooks/` as canonical architecture for new domains; see `AGENTS.md`.

## File structure

```
/
├── CONTEXT-MAP.md             ← portfolio domains + relationships
├── CONTEXT.md                 ← investing ubiquitous language
├── investing/README.md
├── credit/
│   ├── CONTEXT.md             ← credit / CSS ubiquitous language
│   ├── README.md
│   └── docs/                  ← credit feature specs
├── docs/
│   ├── adr/                   ← system-wide ADRs
│   └── mvp/                   ← investing demo specs (delivered / frozen vision)
└── src/                       ← investing demo implementation (migrate later)
```

## Use CONTEXT vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), prefer terms from the **matching domain** CONTEXT file; do not mix investing terms (ROC, EY, model portfolio) with credit terms (scorecard, WOE, PSI).

If the concept you need isn't in the domain CONTEXT yet, either reconsider invented language or note the gap for `/grill-with-docs`.

## Flag ADR conflicts

If your output contradicts an existing ADR or a **closed decision** in investing architecture docs, surface it explicitly rather than silently overriding:

> _Contradicts [decision or ADR] — but worth reopening because…_

Update the ADR or architecture doc before implementing a conflicting change. Phase 2 QV is cancelled (ADR-0003) — do not treat the Phase 2 PRD as ready for implementation.
