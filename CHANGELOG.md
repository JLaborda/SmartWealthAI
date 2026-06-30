# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-30

First public release: the **June 30 demo slice** — a runnable Greenblatt-style Magic Formula pipeline on SimFin US data.

### Added

- **SimFin ETL** — bulk download (`download-simfin`), normalizer (`normalize-simfin`), curated fundamentals with point-in-time keys.
- **Universe construction** — SimFin US market minus banks, insurers, and utilities (`build-universe`).
- **Magic Formula scoring** — ROC (quality), Earnings Yield (cheapness), combined rank with market-cap tie-break (`compute-metrics`, `score-universe`).
- **Model portfolio** — top 30 names, equal-weight.
- **End-to-end CLI** — `run-demo-pipeline` orchestrates ingest → universe → normalize → prices → score for one `run_date`.
- **Streamlit dashboard** — Overview, Ranking, and Portfolio pages (`run-dashboard`).
- **MLflow run logging** — params, metrics, portfolio parquet artifact, and git commit SHA tag per pipeline run.
- **Hermetic CI** — pytest fixtures; no live SimFin or yfinance calls in PR workflows.
- **MVP specs and ADRs** under `docs/mvp/` and `docs/adr/`.

### Requirements

- Python 3.11+, Poetry.
- `SIMFIN_API_KEY` for live data download (see [download-simfin guide](docs/mvp/guides/download-simfin.md)).

### Quickstart

```bash
poetry install
export SIMFIN_API_KEY="<your key>"
poetry run run-demo-pipeline --run-date 2026-06-18
poetry run run-dashboard --data-dir data --run-date 2026-06-18
```

### Known gaps (phase 2)

- Full PIT acceptance audit across all curated rows at scale.
- Automated exclusion-list regression on live ranked universe.
- Production Docker image, AWS ECS deploy, backtesting, sell-watch, paper trading.

[0.1.0]: https://github.com/JLaborda/SmartWealthAI/releases/tag/v0.1.0
