# SmartWealthAI

SmartWealthAI is an MVP-stage quantitative value-investing system for US equities.
The target architecture is a modular, point-in-time-correct pipeline that ingests
financial data, ranks companies with explainable quality and cheapness signals,
backtests the strategy, monitors a paper model portfolio, and reports every
decision through auditable artifacts.

The repository is currently in **MVP planning and CI foundation work**. Canonical
architecture and feature decisions live under `docs/mvp/`; legacy exploration in
older source files or notebooks should not be treated as the product architecture.

## Documentation Map

Start here when changing behavior:

| Path | Purpose |
| --- | --- |
| `docs/README.md` | Index for the documentation tree. |
| `docs/mvp/architecture/architecture.md` | MVP architecture, closed decisions, and cross-cutting constraints. |
| `docs/mvp/features/*.md` | Feature specs for ETL, universe construction, scoring, backtesting, sell-watch, portfolio evolution, dashboard, and paper broker execution. |
| `docs/mvp/prds/ci-cd/ci-cd-prd.md` | CI/CD and MLOps implementation plan. |
| `tests/fixtures/lake/README.md` | Hermetic fixture lake contract used by PR CI. |

## Current Developer Workflow

### Requirements

- Python 3.11
- Poetry

### Install

```bash
poetry install --no-root --with dev
```

or use the shared Make target:

```bash
make install
```

### Lint and Test

```bash
make lint
make test
```

`make lint` runs Ruff checks and format verification. `make test` runs pytest
against committed fixtures only; PR CI must not call SEC EDGAR, `yfinance`, AWS,
or paid data providers.

## Fixture Lake

The first implemented package surface is `smartwealthai.fixture_lake`, a small
helper module for deterministic tests. It loads static, reduced SEC EDGAR and
`yfinance` snapshots from `tests/fixtures/lake/` and exposes a point-in-time
fundamentals query:

```python
from datetime import date

from smartwealthai.fixture_lake import point_in_time_fundamentals

snapshot = point_in_time_fundamentals(decision_date=date(2025, 1, 1))
```

The point-in-time rule is: for a decision date `D`, use only rows where
`as_of_date <= D`, then select the latest known `version_id` per
`(cik, fiscal_period_end)`. This mirrors the ETL/data lake spec while keeping PR
CI hermetic.

## CI Guardrails

The current GitHub Actions workflow runs on pull requests and pushes targeting
`develop` or `main`:

1. Install Poetry dependencies with `make install`.
2. Run `make lint`.
3. Run `make test`.

Integration workflows that touch live providers or AWS are intentionally separate
from PR CI and are still planned. Full backtests, paper trading, Streamlit
deployment, Prefect orchestration, and MLflow infrastructure are also future
MVP steps, not part of the current PR CI baseline.

## Key MVP Constraints

- Point-in-time correctness is mandatory; look-ahead bias is a critical defect.
- Raw provider responses are stored before transformation.
- The MVP is paper trading only; no module may place real broker orders.
- S3 + DuckDB is the target data-lake shape; Athena and Kubernetes are out of
  scope for the MVP.
- Every implementation change should trace to a feature spec in
  `docs/mvp/features/`.
