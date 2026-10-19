# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-19

Portfolio release: Credit CSS demo slice + Spec Kit living canon + uv workspace monorepo (promote of `develop` via [#195](https://github.com/JLaborda/SmartWealthAI/pull/195)).

### Added

- **Credit CSS** — application mart (book sample + AMEX / Home Credit competition paths), competition EDA, WOE/IV + XGBoost scratch scoring (`credit-css fit` / `score`), FastAPI `POST /score` + `POST /drivers`, local PSI CLI (`credit-css psi`), `credit-css doctor` readiness, Friday demo rehearsal guide, bake-image path and ephemeral Fargate CSS serve stretch under `platform/`.
- **Spec Kit** — living feature canon under `specs/`, constitution **1.1.0** (`.specify/memory/constitution.md`), Spec Kit agent skills.
- **Monorepo packaging** — Magic Formula relocated under `investing/`; Poetry → **uv workspace** ([ADR-0005](docs/adr/0005-poetry-to-uv-workspace.md)); lean `credit` / `investing` domain deps; domain CI matrix (`make test-credit` / `make test-investing`).
- **Platform** — ephemeral Fargate CSS serve demo (Terraform + bake/serve path; stretch beyond local Friday demo).

### Fixed

- **Application mart labels** — retain custom non-numeric / non-integral `--bad-value` / `--good-value` labels instead of coercing them to NaN ([#196](https://github.com/JLaborda/SmartWealthAI/pull/196)).

### Changed

- Root install path is **uv** (`uv sync`), not Poetry; investing CLIs remain available via `uv run` from the workspace.

### Requirements

- Python 3.11+, [uv](https://docs.astral.sh/uv/).
- Investing demo: `SIMFIN_API_KEY` for live SimFin download.
- Credit demo: Git LFS for book sample (`git lfs pull --include="credit/data/*"`); optional competition raw extracts under gitignored `data/credit/raw/`.

### Quickstart

```bash
uv sync
# Investing
export SIMFIN_API_KEY="<your key>"
uv run run-demo-pipeline --run-date 2026-06-18
# Credit (hermetic fixture path)
uv run credit-css doctor
uv run credit-css build-application-mart \
  --source credit/tests/fixtures/application_source/applications.csv \
  --output-dir data/credit/application_mart
```

See [credit/docs/guides/friday-demo.md](credit/docs/guides/friday-demo.md) for the full Credit CSS rehearsal.

### Known gaps

- Credit chapter 6 OptBinning scorecard, production monitoring, and deeper explainability.
- Investing phase-2 paths (permanent loss filter, backtesting, sell-watch, paper trading) remain deferred.
- Platform: full AWS cutover / orchestrator choice still open beyond the ephemeral Fargate demo.

[0.2.0]: https://github.com/JLaborda/SmartWealthAI/releases/tag/v0.2.0

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
