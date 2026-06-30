"""MLflow run logging for demo pipeline executions."""

from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

import mlflow
import numpy as np

DEMO_PIPELINE_EXPERIMENT = "demo_pipeline"


def resolve_git_sha() -> str:
    """Return the current git commit SHA, or ``unknown`` when unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown"
    sha = result.stdout.strip()
    return sha or "unknown"


def resolve_tracking_uri(tracking_uri: str | None = None) -> str:
    """Resolve MLflow tracking URI from argument, env, or local default."""
    if tracking_uri is not None:
        return tracking_uri
    env_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if env_uri:
        return env_uri
    return Path.cwd().joinpath("mlruns").as_uri()


def _prepare_file_store(uri: str) -> None:
    # ponytail: MLflow 3.14+ blocks file:// unless opted in; demo slice uses local mlruns
    if uri.startswith("file:"):
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")


def summarize_metric_distribution(values: list[float]) -> dict[str, float]:
    """Return p25/p50/p75 for a metric sample; empty input yields no quantiles."""
    if not values:
        return {}
    arr = np.asarray(values, dtype=float)
    p25, p50, p75 = np.percentile(arr, [25, 50, 75])
    return {"p25": float(p25), "p50": float(p50), "p75": float(p75)}


def log_demo_pipeline_run(
    *,
    tracking_uri: str | None = None,
    experiment_name: str = DEMO_PIPELINE_EXPERIMENT,
    run_date: date,
    formula_version: str,
    universe_count: int,
    portfolio_size: int,
    quality_n_valid: int,
    quality_n_invalid: int,
    cheap_n_valid: int,
    cheap_n_invalid: int,
    rankable_count: int,
    portfolio_count: int,
    roc_values: list[float],
    ey_values: list[float],
    portfolio_parquet: Path,
    git_sha: str | None = None,
) -> str:
    """Log a demo scoring run to MLflow and return the run id."""
    uri = resolve_tracking_uri(tracking_uri)
    _prepare_file_store(uri)
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment_name)

    sha = git_sha if git_sha is not None else resolve_git_sha()

    with mlflow.start_run() as run:
        mlflow.set_tag("git_sha", sha)
        mlflow.set_tag("pipeline", "demo")

        mlflow.log_param("run_date", run_date.isoformat())
        mlflow.log_param("formula_version", formula_version)
        mlflow.log_param("universe_count", universe_count)
        mlflow.log_param("portfolio_size", portfolio_size)

        mlflow.log_metric("quality_n_valid", quality_n_valid)
        mlflow.log_metric("quality_n_invalid", quality_n_invalid)
        mlflow.log_metric("cheap_n_valid", cheap_n_valid)
        mlflow.log_metric("cheap_n_invalid", cheap_n_invalid)
        mlflow.log_metric("rankable_count", rankable_count)
        mlflow.log_metric("portfolio_count", portfolio_count)

        for key, value in summarize_metric_distribution(roc_values).items():
            mlflow.log_metric(f"roc_{key}", value)
        for key, value in summarize_metric_distribution(ey_values).items():
            mlflow.log_metric(f"ey_{key}", value)

        mlflow.log_artifact(str(portfolio_parquet))

        return run.info.run_id
