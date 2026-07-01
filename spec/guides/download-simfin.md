# Download SimFin bulk fundamentals and prices (demo)

Operator guide for the **SimFin bulk connector** on the June 30 demo path. Canonical spec: [`spec/features/006-etl-data-lake/spec.md`](../../features/006-etl-data-lake/spec.md).

## Prerequisites

- Poetry environment installed (`poetry install`)
- `SIMFIN_API_KEY` in the environment (free tier from [simfin.com](https://simfin.com); never commit)

```bash
export SIMFIN_API_KEY="<from user secrets>"
```

## Download US bulk datasets

Downloads demo datasets plus phase 2 multi-period statement variants into the raw lake under `data/raw/simfin/`:

| Dataset | Variant | Lake partition | Critical |
| --- | --- | --- | --- |
| `companies` | `default` | `dataset=companies/variant=default/market=us/` | yes |
| `industries` | `default` | `dataset=industries/variant=default/market=us/` | yes |
| `income` | `ttm` | `dataset=income/variant=ttm/market=us/` | yes |
| `balance` | `quarterly` | `dataset=balance/variant=quarterly/market=us/` | yes |
| `cashflow` | `ttm` | `dataset=cashflow/variant=ttm/market=us/` | no |
| `shareprices` | `latest` | `dataset=shareprices/variant=latest/market=us/` | yes |
| `income` | `annual` | `dataset=income/variant=annual/market=us/` | no |
| `income` | `quarterly` | `dataset=income/variant=quarterly/market=us/` | no |
| `balance` | `annual` | `dataset=balance/variant=annual/market=us/` | no |
| `cashflow` | `annual` | `dataset=cashflow/variant=annual/market=us/` | no |
| `cashflow` | `quarterly` | `dataset=cashflow/variant=quarterly/market=us/` | no |

Each partition also includes `as_of_date=<YYYY-MM-DD>/` and the verbatim SimFin CSV filename (e.g. `us-income-ttm.csv`).

```bash
poetry run download-simfin
poetry run download-simfin --data-dir data --refresh-days 7
poetry run download-simfin --as-of-date 2026-06-18 --force
```

This command writes raw snapshots only. Run the full demo pipeline in order:

```bash
poetry run download-simfin --as-of-date 2026-06-18
poetry run build-universe --run-date 2026-06-18
poetry run normalize-simfin --snapshot-date 2026-06-18 --universe-run-date 2026-06-18
poetry run download-prices --run-date 2026-06-18 --snapshot-date 2026-06-18
poetry run compute-metrics --ticker AAPL --as-of-date 2026-06-18
```

Or run ingest → score in one command (then launch the dashboard):

```bash
poetry run run-demo-pipeline --run-date 2026-06-18
poetry run run-demo-pipeline --run-date 2026-06-18 --skip-download
poetry run run-dashboard --data-dir data --run-date 2026-06-18
```

Pass `--ticker` to limit the normalize step to specific names (intersect universe). Use `compute-metrics` for single-ticker ROC/EY smoke tests without a full scoring run.

`normalize-simfin` requires `--universe-run-date` (after `build-universe`) or `--ticker` for smoke tests. It does not process the full SimFin US table by default.

Phase 2 annual/quarterly rows require the matching cashflow variant on disk; missing QV inputs route to `curated/issues/` with reason `missing_qv_inputs`.

## Daily price history (phase 2)

Backtests and historical market cap need **full daily adjusted prices**, not the demo `shareprices/latest` snapshot. Use `download-price-history` after `build-universe` (or pass `--ticker` for smoke tests).

```bash
poetry run download-price-history \
  --universe-run-date 2026-06-18 \
  --start-date 2016-01-01 \
  --end-date 2026-06-18 \
  --snapshot-date 2026-06-18
```

| Step | Output |
| --- | --- |
| SimFin bulk download | `raw/simfin/dataset=shareprices/variant=daily/market=us/as_of_date=<date>/us-shareprices-daily.csv` |
| Normalize + partition | `curated/prices/ticker=<T>/year=<YYYY>/prices.parquet` |

Curated columns: `ticker`, `price_date`, `close`, `adj_close`, `volume`. Use `lookup_daily_adj_close()` from `price_history_ingest` for the latest `adj_close` on or before a rebalance date.

**Free-tier notes:** `shareprices/daily` is a large bulk file. Re-download weekly (`--refresh-days 7`, default) unless `--force`. The demo pipeline does **not** call this step. Per-ticker yfinance fallback is deferred; see phase 2 architecture when SimFin limits block a backfill.

Flags: `--skip-download` (offline/tests), `--force` (overwrite raw + curated partitions), `--ticker` (repeatable).

## Refresh and cache behaviour

- **Skip:** Re-run without `--force` when the on-disk lake copy is younger than `--refresh-days` (default `7`).
- **Force:** `--force` re-downloads from SimFin and overwrites today's partition regardless of age.
- **SimFin package cache:** Intermediate downloads land in `data/cache/simfin/` before being copied into `raw/simfin/`.

## Failures

- A failure for one dataset does not stop the rest.
- Non-critical datasets (`cashflow`, phase 2 statement variants) failure still exits `0` when critical datasets succeed.
- Exit code `1` when all critical datasets (`companies`, `industries`, `income/ttm`, `balance/quarterly`, `shareprices`) fail, or when `SIMFIN_API_KEY` is missing.
- Per-run errors are written to `raw/simfin/download_runs/as_of_date=<date>/errors.json` when any dataset fails.

## Module map

| Module | Role |
| --- | --- |
| `smartwealthai.simfin_client` | Configure API key, safe bulk download (zip-slip guarded), resolve cache CSV path. |
| `smartwealthai.download_simfin` | CLI orchestration, skip/force logic, run summary. |
| `smartwealthai.price_history_ingest` | Phase 2 daily price normalize + run-date lookup. |
| `smartwealthai.download_price_history` | CLI for `shareprices/daily` → curated ticker/year partitions. |
| `smartwealthai.lake_paths` | Raw lake path builders for `raw/simfin/`. |

## Tests

Hermetic tests live in `tests/test_download_simfin.py` and `tests/test_price_history_ingest.py`. They mock SimFin network calls; PR CI does not require a live API key.
