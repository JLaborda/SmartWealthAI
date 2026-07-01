# Tech stack

Technologies, infrastructure, and runtime conventions for SmartWealthAI.
## Infrastructure (AWS, cheapest-first)


| Area | Decision |
| --- | --- |
| Storage | S3 (raw + curated parquet) + DuckDB as the local query engine. No Athena bill. |
| Experiment tracking | MLflow from day one. Tracking server on a small EC2 (SQLite backend) with `s3://` as the artifact root. |
| Dashboard | Streamlit. |
| Email alerts | AWS SES (sporadic emails, very cheap). |
| Compute / runtime | ECS Fargate Spot tasks (or AWS Batch on Fargate Spot), whichever is cheaper for the daily run. Triggered by Prefect. |
| Orchestration | Prefect Core (self-hosted on the same EC2 as MLflow, or via Prefect Cloud free tier). |
| Scheduling | EventBridge cron triggers the Prefect deployment once per day. |
| CI/CD | GitHub Actions builds and pushes Docker images to ECR. |
| Observability | CloudWatch Logs + Prefect UI for the MVP. Per-module metrics added if/when needed. |


## MLOps stack (cost-aware)

User proposed: GitHub Actions + MLflow + Prefect + Kubernetes.

For a daily run over the S&P 500 historical universe, Kubernetes is overkill and expensive. Recommended cost-aware mapping:

| User goal | MVP-cheap option | Growth path |
| --- | --- | --- |
| Orchestration | Prefect Core running on a small EC2 (or Prefect Cloud free tier) | Prefect on EKS |
| Execution | AWS Batch or ECS Fargate spot tasks triggered by Prefect, or a small EC2 with cron + Docker | EKS with autoscaling |
| Experiment tracking | MLflow with SQLite + S3 artifact root, on the same EC2 | MLflow on RDS + EC2 / Fargate |
| CI/CD | GitHub Actions building Docker images and pushing to ECR | Same |
| Scheduling | EventBridge cron triggering a Prefect deployment | Same |
| Secrets | GitHub Secrets in CI; AWS Secrets Manager at runtime | Same |
| Observability | CloudWatch Logs + Prefect UI | CloudWatch Logs + Prefect Cloud + Grafana |

This still showcases MLOps competence (CI/CD, container build, orchestrator, experiment tracking, secrets, observability) without paying for EKS in the MVP.


## MLflow

User question: "are immutable snapshots like artifacts? What if we used MLflow?"

Yes. MLflow is a natural fit here, and it covers three needs at once:

- **Runs**: each pipeline execution (daily, plus every backtest) is logged as an MLflow run. Parameters (universe definition, rebalance frequency, weighting scheme, thresholds, git commit SHA) are logged via `mlflow.log_param`. Metrics (Sharpe, drawdown, CAGR, hit rate, alpha, number of exclusions, count of sell signals) are logged via `mlflow.log_metric`.
- **Artifacts**: the curated input slice (or its hash), the watchlist, the model portfolio, the backtest report, and the markdown / HTML dashboard snapshot are logged as artifacts. The artifact store points at S3 with versioning and / or object lock so a past run is byte-for-byte recoverable.
- **Model registry (optional, future)**: when the scoring model evolves beyond the Greenblatt placeholder, MLflow's model registry can promote a candidate from `staging` to `production` and tie that decision back to a backtest run.

Practical MVP setup:

- MLflow tracking server: a tiny EC2 (or AWS Fargate task on demand) with SQLite or RDS Postgres as the backend store. For the absolute cheapest setup, an MLflow tracking server is not strictly required: `mlflow.start_run(...)` with `file://` or `s3://` as the artifact root works for a single user.
- Artifact root: `s3://smartwealthai-mlflow-artifacts/`.
- Each run is tagged with the commit SHA and pipeline name, which makes the "immutable snapshot" effectively the MLflow run id.

Treating this as nice-to-have for the MVP is fine: we can start by writing snapshots straight to S3 with predictable paths, and slot in MLflow once the pipeline stabilizes.


## Runtime (local development)

- **Python:** 3.11+ (`requires-python = "^3.11"` in `pyproject.toml`)
- **Dependencies:** Poetry

```bash
poetry env use python3.11
poetry install
poetry run pytest
```

### MLflow (demo pipeline runs)

`mlflow-skinny` is a Poetry dependency. No local MLflow UI server is required for pipeline logging.

```bash
export MLFLOW_TRACKING_URI="file://$(pwd)/mlruns"
export MLFLOW_ALLOW_FILE_STORE=true
```

### Secrets

- **Local dev:** `.env` (gitignored) for `SIMFIN_API_KEY`; devcontainer loads via `.devcontainer/install-env-hook.sh`
- **CI:** GitHub Actions secrets
- **Cloud runtime:** AWS Secrets Manager

### Data lake (technical)

- S3 raw + curated parquet zones; DuckDB as analytical engine
- Provider connectors: SimFin (demo), SEC EDGAR (phase 2 spike frozen)
- Cache: `yfinance` responses on S3 under `s3://smartwealthai-cache/yfinance/` (phase 2)

## CI/CD and tooling PRDs

| PRD | Path |
| --- | --- |
| Devcontainer | [`spec/prds/devcontainer/prd.md`](../prds/devcontainer/prd.md) |
| CI/CD | [`spec/prds/ci-cd/ci-cd-prd.md`](../prds/ci-cd/ci-cd-prd.md) |
| Phase 2 coordination | [`spec/prds/phase2/prd.md`](../prds/phase2/prd.md) |

## Operator guides

| Guide | Path |
| --- | --- |
| SimFin download (demo) | [`spec/guides/download-simfin.md`](../guides/download-simfin.md) |
| SEC fundamentals (frozen spike) | [`spec/guides/download-fundamentals.md`](../guides/download-fundamentals.md) |
