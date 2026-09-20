# Demo pipeline operator guide

End-to-end runbook for the June 30 demo slice: SimFin ingest → universe → normalize → run-date prices → Magic Formula score → Streamlit dashboard.

Canonical specs: [`006-etl-data-lake`](../features/006-etl-data-lake/spec.md), [`011-universe-construction`](../features/011-universe-construction/spec.md), [`007-high-quality-stocks`](../features/007-high-quality-stocks/spec.md), [`003-cheap-stocks`](../features/003-cheap-stocks/spec.md), [`005-dashboard-reporting`](../features/005-dashboard-reporting/spec.md). SimFin download details: [`download-simfin.md`](download-simfin.md).

## Intent

Replay one decision date (`run_date`) from raw SimFin bulk files to a top-30 equal-weight model portfolio. Scoring reads **curated parquet only**. The demo path does **not** call `download-price-history` (that CLI is phase 2 backtest NAV).

## Prerequisites

- Python 3.11+, `poetry install`
- `SIMFIN_API_KEY` for live download (copy `.env.example` → `.env` locally; never commit)
- A `run_date` you will reuse across every stage and the dashboard

```bash
export SIMFIN_API_KEY="<from user secrets>"
poetry run run-demo-pipeline --run-date 2026-06-18
poetry run run-dashboard --data-dir data --run-date 2026-06-18
```

`--skip-download` reuses an existing `data/raw/simfin/` tree (offline / CI-style). `--force` re-downloads SimFin bulk and rebuilds the run-date price snapshot.

## Pipeline stages

`run-demo-pipeline` runs these CLIs in order and **aborts** if `download-simfin` exits non-zero or `download-prices` finds no priced tickers.

| Stage | CLI | Writes |
| --- | --- | --- |
| 1. Raw ingest | `download-simfin` | `raw/simfin/dataset=*/variant=*/market=us/as_of_date=<date>/` |
| 2. Universe | `build-universe` | `curated/universe/run_date=<date>/universe.parquet`, `exclusions.parquet` |
| 3. Fundamentals | `normalize-simfin` | `curated/fundamentals/cik=*/period=*/fundamentals.parquet`, `curated/issues/run_date=<date>/fundamentals.parquet` |
| 4. Demo prices | `download-prices` | `curated/prices/run_date=<date>/prices.parquet` |
| 5. Score + portfolio | `score-universe` | quality / cheap / combined ranks, portfolio, review queues (see below) |

Equivalent manual sequence:

```bash
poetry run download-simfin --as-of-date 2026-06-18
poetry run build-universe --run-date 2026-06-18
poetry run normalize-simfin --snapshot-date 2026-06-18 --universe-run-date 2026-06-18
poetry run download-prices --run-date 2026-06-18 --snapshot-date 2026-06-18
poetry run score-universe --run-date 2026-06-18
```

`--snapshot-date` selects the **raw SimFin partition**. It defaults to `--run-date` on the orchestrator. Keep them equal unless you are replaying a newer decision date against an older bulk download.

### Orchestrator flags (`run-demo-pipeline`)

| Flag | Effect |
| --- | --- |
| `--run-date` (required) | Decision date for universe, PIT metrics, prices, scoring |
| `--snapshot-date` | Raw bulk partition (default: run date) |
| `--ticker` (repeatable) | Intersect normalize scope with these tickers |
| `--portfolio-size` | Top-N equal-weight holdings (default `30`) |
| `--skip-mlflow` | Skip MLflow logging (hermetic tests) |
| `--refresh-days` | Skip SimFin re-download when raw files are younger (default `7`) |
| `--force` | Re-download SimFin bulk and rebuild curated prices |
| `--skip-download` | Skip stage 1; use existing raw lake |
| `--data-dir` | Lake root (default `data`) |

`--ticker` does **not** shrink universe construction or price ingest. It only intersects the normalizer ticker set with the universe.

## Scoring artifacts

`score-universe` ranks every universe ticker that has both a valid ROC and a valid EY (`formula_version` `v1`). Combined rank = ROC rank + EY rank (lower is better); ties break toward **smaller** market cap.

| Artifact | Path |
| --- | --- |
| ROC scores | `curated/scores/quality/run_date=<date>/scores.parquet` |
| EY scores | `curated/scores/cheap/run_date=<date>/scores.parquet` |
| Combined ranking | `curated/scores/combined/run_date=<date>/ranking.parquet` |
| Model portfolio | `curated/portfolio/run_date=<date>/portfolio.parquet` |
| Quality review queue | `curated/issues/run_date=<date>/quality.parquet` |
| Cheapness review queue | `curated/issues/run_date=<date>/cheap.parquet` |

Single-ticker smoke test (needs universe + curated fundamentals + run-date prices):

```bash
poetry run compute-metrics --ticker AAPL --as-of-date 2026-06-18
```

The standalone `score-universe` CLI always logs MLflow. Only `run-demo-pipeline --skip-mlflow` (or the `score_universe(..., skip_mlflow=True)` Python API) skips it.

## MLflow

After scoring, `log_demo_pipeline_run` writes experiment `demo_pipeline`:

- Tracking URI: `MLFLOW_TRACKING_URI`, else `file://$(pwd)/mlruns`
- File store: `MLFLOW_ALLOW_FILE_STORE=true` is set automatically for `file:` URIs (required on MLflow 3.14+)
- Tags: `git_sha`, `pipeline=demo`
- Params: `run_date`, `formula_version`, `universe_count`, `portfolio_size`
- Metrics: valid/invalid counts, `rankable_count`, `portfolio_count`, ROC/EY p25/p50/p75
- Artifact: the portfolio parquet

`mlruns/` is gitignored. Point `MLFLOW_TRACKING_URI` at a remote server **before** scoring if you need a shared UI; local `mlruns/` are not visible to a remote server after the fact.

## Dashboard

Shipped surface is **three pages** (`apps/dashboard/`): Overview, Ranking, Portfolio. The dashboard reads `curated/scores/combined/.../ranking.parquet` and `curated/portfolio/.../portfolio.parquet` only — no live SimFin or yfinance.

```bash
poetry run run-dashboard --data-dir data --run-date 2026-06-18
```

- Binds Streamlit to `0.0.0.0:8501` (`--server.headless=true`).
- Env: `SMARTWEALTHAI_DATA_DIR`, `SMARTWEALTHAI_RUN_DATE` (CLI flags set these).
- If `--run-date` / env / `?run_date=` are omitted, the app picks the newest `curated/portfolio/run_date=*` partition.
- Empty state: “Run `score-universe` first.”

## Universe exclusions

`build-universe` drops SimFin US names whose `IndustryId` is in `data/reference/simfin_industry_exclusions.csv` (banks, insurers, utilities), plus a bank/insurance statement-index sanity check. After SimFin industry labels change:

```bash
poetry run generate-simfin-industry-exclusions \
  --industries data/raw/simfin/dataset=industries/variant=default/market=us/as_of_date=2026-06-18/industries.csv
```

Commit the regenerated CSV; it is versioned under `data/reference/`.

## Phase 2 (not in `run-demo-pipeline`)

Daily adjusted prices for backtests (issue #88):

```bash
poetry run download-price-history \
  --universe-run-date 2026-06-18 \
  --start-date 2016-01-01 \
  --end-date 2026-06-18 \
  --snapshot-date 2026-06-18
```

Requires `--universe-run-date` and/or `--ticker`. Curated layout: `curated/prices/ticker=<T>/year=<YYYY>/prices.parquet`. Lookup: `lookup_daily_adj_close()` (latest `adj_close` on or before a date). See [`download-simfin.md`](download-simfin.md).

Multi-period annual/quarterly fundamentals ship with `download-simfin` / `normalize-simfin`. History API: `load_pit_fundamentals_history(data_dir, ticker=..., as_of_date=...)` — annual/quarterly rows only, PIT-filtered.

## Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `SIMFIN_API_KEY is not set` | Missing env | Export the key; do not rely on `.env` in CI or cloud agents |
| Pipeline stops after download | Critical SimFin datasets failed | Inspect `raw/simfin/download_runs/as_of_date=<date>/errors.json` |
| `Universe not found` on normalize | Stage 2 skipped or wrong `--universe-run-date` | Run `build-universe` for the same date |
| Normalize processes nothing useful | `--ticker` does not intersect the universe | Drop `--ticker` or pick names that survived exclusions |
| `download-prices` exit 1 | No `shareprices/latest` rows on or before `run_date` | Confirm raw partition; missing tickers go to `curated/prices/download_runs/run_date=<date>/errors.json` |
| Dashboard empty | Scoring not run, or `--run-date` mismatch | Re-run `score-universe` / `run-demo-pipeline` with the same date |
| MLflow file-store error | MLflow 3.14+ without opt-in | Pipeline sets `MLFLOW_ALLOW_FILE_STORE`; export it if you call `mlflow` yourself |
| Re-run still uses old prices | Curated snapshot already exists | Pass `--force` on `download-prices` or `run-demo-pipeline` |

## Module map

| Module | Role |
| --- | --- |
| `smartwealthai.run_demo_pipeline` | Orchestrator CLI |
| `smartwealthai.download_simfin` | Raw SimFin bulk |
| `smartwealthai.universe_builder` / `build_universe` | Investable universe |
| `smartwealthai.simfin_normalizer` / `normalize_simfin` | PIT curated fundamentals |
| `smartwealthai.price_ingest` / `download_prices` | Run-date `shareprices/latest` snapshot |
| `smartwealthai.magic_formula_ranking` / `score_universe` | ROC + EY ranks + top-N portfolio |
| `smartwealthai.mlflow_run_logging` | Demo experiment logging |
| `smartwealthai.run_dashboard` / `dashboard_data` | Streamlit launcher + parquet readers |
| `smartwealthai.compute_metrics` | Single-ticker ROC/EY tracer |
| `smartwealthai.price_history_ingest` | Phase 2 daily prices (not in demo orchestrator) |

Hermetic tests: `tests/test_run_demo_pipeline.py`, `tests/test_magic_formula_ranking.py`, `tests/test_dashboard_data.py`. PR CI does not call SimFin or yfinance live.
