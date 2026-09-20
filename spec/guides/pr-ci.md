# PR CI and coverage

Operator guide for the hermetic pull-request gate. Canonical spec: [`014-cicd-infrastructure`](../features/014-cicd-infrastructure/spec.md). Product CI/CD plan: [`ci-cd-prd.md`](../prds/ci-cd/ci-cd-prd.md).

## What runs

Workflow: [`.github/workflows/pr-ci.yml`](../../.github/workflows/pr-ci.yml) (`Tests`).

Triggers: pull requests and pushes to `develop` / `main`, plus `workflow_dispatch`.

| Step | Command |
| --- | --- |
| Install | `make install` → `poetry install --with dev` |
| Lint | `make lint` → `ruff check .` and `ruff format --check .` |
| Tests + coverage XML | `poetry run pytest --cov=smartwealthai --cov-report=term-missing --cov-report=xml` |
| Upload | `codecov/codecov-action@v5` with `fail_ci_if_error: true` |

Python **3.11**. No AWS credentials. No live SimFin, SEC, or yfinance calls.

Local equivalents:

```bash
make install
make lint
make test          # pytest + terminal coverage (no XML, no Codecov upload)
make format        # ruff format (not run in CI; CI only --check)
```

To match CI coverage upload locally:

```bash
poetry run pytest --cov=smartwealthai --cov-report=term-missing --cov-report=xml
```

There is **no** `make test-smoke` target. The PRD still lists it as a Phase 0 idea; hermetic pytest (including pipeline CLI tests) is the smoke gate.

## Codecov gates

[`codecov.yml`](../../codecov.yml) is the source of truth. It complements `[tool.coverage.*]` in `pyproject.toml`.

| Check | Rule | Meaning |
| --- | --- | --- |
| **Project** | `target: auto`, `threshold: 1%` | Total coverage must not drop more than 1% vs the PR base |
| **Patch** | `target: 85%`, `threshold: 2%` | New/changed lines must be ≥ ~83% covered |

PR comments use layout `reach,diff,flags,files` and only post when the diff has coverage-relevant changes (`require_changes: true`).

### Ignored / omitted paths

Same frozen SEC spike as Poetry coverage `omit` — not counted toward demo metrics:

- `tests/**`
- `src/smartwealthai/sec_client.py`
- `src/smartwealthai/edgartools_client.py`
- `src/smartwealthai/download_fundamentals.py`

`pytest` marker `integration` exists for network/AWS tests and is **excluded from this workflow** (the job never passes `-m integration`).

## Patch coverage failures

Codecov 85% patch is enforced on PRs (added in [#119](https://github.com/JLaborda/SmartWealthAI/issues/119) / `codecov.yml`). Typical fail: new branches in ETL or CLI without a hermetic test.

1. Open the Codecov PR comment (diff / files).
2. Add a fixture test under `tests/` that exercises the new branch **without network**.
3. Re-run `make test` and confirm the uncovered lines disappear from `--cov-report=term-missing`.

Do not lower the patch target to land a feature. Do not call live SimFin in PR tests — mock `fetch_dataset_csv` / use `tests/fixtures/lake/`.

## Constraints

- **Hermetic:** fixtures under `tests/fixtures/lake/` (see that README). Point-in-time tests must filter `as_of_date <= decision_date`.
- **`data/` is gitignored** except `data/reference/**`. CI never sees a developer lake.
- **Secrets:** `CODECOV_TOKEN` is a GitHub Actions secret. `SIMFIN_API_KEY` is **not** required for PR CI.
- M2 Terraform plan/apply, ingest-smoke, and ECS deploy are **out of this workflow**.
