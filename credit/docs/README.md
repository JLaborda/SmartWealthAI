# Credit documentation

Feature specs for the credit / CSS domain live **here** (`credit/docs/`), not under `docs/mvp/features/`.

Investing Magic Formula specs remain in [`docs/mvp/`](../docs/mvp/) until a migrate-only PR.

## Layout

```text
credit/docs/
  README.md
  features/
    css-chapter5-mart-and-scoring.md   # Chapter 5 parent spec (PR1 mart + PR2 scratch scoring + serving)
    psi-data-drift.md                  # Local PSI data-drift CLI (Friday MUST)
    aws-fargate-serve-demo.md          # Ephemeral CSS FastAPI on Fargate (Terraform stretch)
  guides/
    serve-fastapi.md                   # Fit → joblib → FastAPI /score + /drivers
    friday-demo.md                     # 10 min rehearsal (fit → serve → Docker → PSI)

platform/docs/
  ephemeral-css-serve-demo.md          # Stretch: Fargate demo-up / demo-down (#174)
```

## Before writing a feature

1. Read [`../CONTEXT.md`](../CONTEXT.md) and [`../../CONTEXT-MAP.md`](../../CONTEXT-MAP.md).
2. Create or extend a spec under `features/` before coding.
3. Keep MVP scope aligned with credit README delivery cuts: book smoke → **competition raw (#151) → competition mart (#152) → competition EDA (#153) → scratch scoring (#145)**.

Book-sample EDA smoke: [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) (done). Competition-mart EDA: [#153](https://github.com/JLaborda/SmartWealthAI/issues/153).
