# SmartWealthAI

SmartWealthAI is a spec-driven MVP for a modular quantitative value investing system. The target system builds a point-in-time US equities universe, scores quality and cheapness with a Greenblatt-style workflow, validates the strategy through backtests, and produces paper-trading orders with auditable explanations.

The repository is currently in MVP planning and specification refinement. The canonical product and technical scope live under `docs/mvp/`; there is no runnable production pipeline or CLI entry point in this branch yet.

## Documentation Map

Start here when changing the system:

| Path | Purpose |
| --- | --- |
| [`docs/README.md`](docs/README.md) | Index for the documentation tree and spec workflow. |
| [`docs/mvp/architecture/architecture.md`](docs/mvp/architecture/architecture.md) | MVP architecture, closed decisions, cross-module constraints, and acceptance criteria. |
| [`docs/mvp/features/`](docs/mvp/features/) | One feature spec per subsystem, including scope, inputs, outputs, flow, risks, and acceptance criteria. |
| [`CONTEXT.md`](CONTEXT.md) | Shared domain vocabulary for value investing concepts used across specs and future code. |
| [`AGENTS.md`](AGENTS.md) | Working instructions for coding agents and contributors. |

Historical Sprint 0 requirements are retained in `docs/mvp/requirements/requirements.md`, but they are superseded by the MVP architecture and feature specs.

## MVP Constraints

Keep new specs and implementation aligned with these decisions:

- Point-in-time correctness is mandatory. Historical ranking and backtesting may only use data available on or before the decision date.
- Raw provider responses are stored before transformation so downstream bugs can be replayed from source.
- The MVP is US equities only, using historical S&P 500 constituents and excluding banks, insurers, and utilities.
- The first ranking model is Greenblatt-style: `ROC` for quality plus `Earnings Yield` for cheapness.
- Permanent capital loss checks are hard exclusions, focused on fraud and bankruptcy for the MVP.
- Broker integration is paper trading only and requires manual confirmation for sell-watch signals.
- Backtesting must pass before broker order generation; the strategy must beat all configured benchmark Sharpes.
- Every run should be reproducible through versioned data, rule versions, git commit SHA, and MLflow or S3 snapshots.

## Developer Setup

Runtime and dependency management are defined in `pyproject.toml`.

```bash
poetry env use python3.13
poetry install
```

The declared runtime is Python 3.13+. The current dependency set is intentionally small while the MVP specs stabilize:

- `pandas`
- `yfinance`

There is no project-wide test suite or linter configured yet. Add tooling only when it is required by an implementation spec.

## Working With Specs

1. Read `docs/mvp/architecture/architecture.md` before changing a subsystem.
2. Open the related feature spec in `docs/mvp/features/`.
3. If the behavior is not specified, update the spec first and record decisions or open questions.
4. Implement only what the spec allows for the current phase.
5. After implementation, update the same spec with status, acceptance criteria, and links to code paths.

## Common Pitfalls

- Do not treat exploratory `src/` or `notebooks/` work as canonical architecture if those directories are added later; MVP specs remain the source of truth.
- Do not introduce look-ahead bias through restated fundamentals, current index membership, ticker changes, delistings, or data published after the decision date.
- Do not commit raw broker exports, personal finance files, secrets, or raw provider downloads. Local and generated data belongs under ignored `data/` paths unless a spec explicitly calls for a small reference file in git.
- Do not add live trading behavior during the MVP. Broker execution is paper-only by design.