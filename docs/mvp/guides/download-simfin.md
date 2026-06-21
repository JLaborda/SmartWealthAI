# Download SimFin bulk fundamentals and prices (demo)

Operator guide for the **SimFin bulk connector** on the June 30 demo path. Canonical spec: [`etl-data-lake.md`](../features/etl-data-lake.md).

## Prerequisites

- Poetry environment installed (`poetry install`)
- `SIMFIN_API_KEY` in the environment (free tier from [simfin.com](https://simfin.com); never commit)

```bash
export SIMFIN_API_KEY="<from user secrets>"
```

## Download US bulk datasets

Downloads six demo datasets into the raw lake under `data/raw/simfin/`:

| Dataset | Variant | Lake partition |
| --- | --- | --- |
| `companies` | `default` | `dataset=companies/variant=default/market=us/` |
| `industries` | `default` | `dataset=industries/variant=default/market=us/` |
| `income` | `ttm` | `dataset=income/variant=ttm/market=us/` |
| `balance` | `quarterly` | `dataset=balance/variant=quarterly/market=us/` |
| `cashflow` | `ttm` | `dataset=cashflow/variant=ttm/market=us/` |
| `shareprices` | `latest` | `dataset=shareprices/variant=latest/market=us/` |

Each partition also includes `as_of_date=<YYYY-MM-DD>/` and the verbatim SimFin CSV filename (e.g. `us-income-ttm.csv`).

```bash
poetry run download-simfin
poetry run download-simfin --data-dir data --refresh-days 7
poetry run download-simfin --as-of-date 2026-06-18 --force
```

This command writes raw snapshots only. The demo price snapshot is built later by `poetry run download-prices` after the universe exists.

```bash
poetry run build-universe --run-date 2026-06-18
poetry run download-prices --run-date 2026-06-18 --snapshot-date 2026-06-18
```

## Refresh and cache behaviour

- **Skip:** Re-run without `--force` when the on-disk lake copy is younger than `--refresh-days` (default `7`).
- **Force:** `--force` re-downloads from SimFin and overwrites today's partition regardless of age.
- **SimFin package cache:** Intermediate downloads land in `data/cache/simfin/` before being copied into `raw/simfin/`.

## Failures

- A failure for one dataset does not stop the rest.
- Non-critical dataset (`cashflow`) failure still exits `0` when critical datasets succeed.
- Exit code `1` when all critical datasets (`companies`, `industries`, `income`, `balance`, `shareprices`) fail, or when `SIMFIN_API_KEY` is missing.
- Per-run errors are written to `raw/simfin/download_runs/as_of_date=<date>/errors.json` when any dataset fails.

## Module map

| Module | Role |
| --- | --- |
| `smartwealthai.simfin_client` | Configure API key, safe bulk download (zip-slip guarded), resolve cache CSV path. |
| `smartwealthai.download_simfin` | CLI orchestration, skip/force logic, run summary. |
| `smartwealthai.lake_paths` | Raw lake path builders for `raw/simfin/`. |

## Tests

Hermetic tests live in `tests/test_download_simfin.py`. They mock SimFin network calls; PR CI does not require a live API key.
