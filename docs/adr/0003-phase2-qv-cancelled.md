---
status: accepted
---

# Phase 2 Quantitative Value — cancelled for active execution

**Decision:** Do **not** execute the Phase 2 Quantitative Value path (forensics, FS-Score funnel, production QV scoring, light/full backtest, sell-watch as the investing production roadmap) as an active delivery track in this repository.

**Why:** Portfolio focus moved to a multi-domain layout with **credit CSS** next ([`CONTEXT-MAP.md`](../../CONTEXT-MAP.md)). Continuing QV as the investing “north star” contradicts the manager-facing roadmap and splits execution capacity.

**What stays delivered:** The June 30 **Magic Formula** demo slice (SimFin → ROC/EY → top-30 EW model portfolio → Streamlit + MLflow) remains the investing delivery ([ADR-0002](0002-june-demo-scope-cut.md), [`demo-slice.md`](../mvp/demo-slice.md)).

**Where cancelled work lives:** Branch `archive/phase2-qv` and historical docs under `docs/mvp/` (architecture vision, Phase 2 PRD, deferred feature specs). Those documents are **frozen reference**, not a live implementation plan.

**Cloud / platform:** Shared AWS / Terraform / orchestration returns later under `platform/`, after domain demos work locally — not as a daily QV job.

**Consequences:**

- Update agent and human entry points (`AGENTS.md`, root README, CONTEXT-MAP) so they do not treat Phase 2 QV as ready for implementation.
- [`docs/mvp/prds/phase2/prd.md`](../mvp/prds/phase2/prd.md) status is **Cancelled**.
- [`docs/mvp/architecture/architecture.md`](../mvp/architecture/architecture.md) is a **frozen historical vision** for the investing module, not an active QV north star.
- Gray & Carlisle *Quantitative Value* remains a cited Source for provenance only; do not implement the QV funnel unless this ADR is superseded.
