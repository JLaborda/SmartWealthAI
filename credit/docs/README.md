# Credit documentation

**Feature specs** for credit / CSS live under Spec Kit: [`specs/`](../../specs/README.md)
(especially [`013-css-chapter5-mart-and-scoring`](../../specs/013-css-chapter5-mart-and-scoring/spec.md),
[`014-psi-data-drift`](../../specs/014-psi-data-drift/spec.md),
[`015-aws-fargate-serve-demo`](../../specs/015-aws-fargate-serve-demo/spec.md)).

This tree keeps **operator guides** under `guides/`. The `features/` directory holds former feature-document **redirect stubs** only — do not edit them as canonical specifications (use `specs/` instead).

## Layout

```text
specs/                             # Canonical feature specs (Spec Kit)
  013-css-chapter5-mart-and-scoring/
  014-psi-data-drift/
  015-aws-fargate-serve-demo/

credit/docs/
  README.md
  features/                        # redirect stubs → specs/
  guides/
    serve-fastapi.md               # Fit → joblib → FastAPI /score + /drivers
    friday-demo.md                 # 10 min rehearsal (fit → serve → Docker → PSI)

platform/docs/
  ephemeral-css-serve-demo.md      # Stretch: Fargate demo-up / demo-down (#174)
```

## Before writing a feature

1. Read [`../CONTEXT.md`](../CONTEXT.md) and [`../../CONTEXT-MAP.md`](../../CONTEXT-MAP.md).
2. Create or extend a Spec Kit feature under `specs/` (`/speckit-specify` or Living Spec) before coding.
3. Keep MVP scope aligned with credit README delivery cuts: book smoke → **competition raw (#151) → competition mart (#152) → competition EDA (#153) → scratch scoring (#145)**.

Book-sample EDA smoke: [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) (done). Competition-mart EDA: [#153](https://github.com/JLaborda/SmartWealthAI/issues/153).
