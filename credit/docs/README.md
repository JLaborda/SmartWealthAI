# Credit documentation

Feature specs for the credit / CSS domain live **here** (`credit/docs/`), not under `docs/mvp/features/`.

Investing Magic Formula specs remain in [`docs/mvp/`](../docs/mvp/) until a migrate-only PR.

## Layout

```text
credit/docs/
  README.md
  features/
    css-chapter5-mart-and-scoring.md   # Chapter 5 parent spec (PR1 mart + PR2 scratch scoring)
```

## Before writing a feature

1. Read [`../CONTEXT.md`](../CONTEXT.md) and [`../../CONTEXT-MAP.md`](../../CONTEXT-MAP.md).
2. Create or extend a spec under `features/` before coding.
3. Keep MVP scope aligned with credit README delivery cuts (PR1 mart → EDA notebook → PR2 chapter 5 scratch model).

EDA: [#147](https://github.com/JLaborda/SmartWealthAI/issues/147) — notebook on the **application mart** after PR1; exploration only, not a substitute for package/CLI.
