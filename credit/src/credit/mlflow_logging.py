"""MLflow logging for CSS fit runs (#145). Credit-local — no investing imports."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import mlflow

CSS_EXPERIMENT = "credit_css_scratch"


def resolve_tracking_uri(tracking_uri: str | None = None) -> str:
    if tracking_uri is not None:
        return tracking_uri
    env_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if env_uri:
        return env_uri
    return Path.cwd().joinpath("mlruns").as_uri()


def _prepare_file_store(uri: str) -> None:
    # ponytail: MLflow 3.14+ blocks file:// unless opted in
    if uri.startswith("file:"):
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")


def log_fit_run(
    *,
    artifact_path: Path,
    params: dict[str, Any],
    metrics: dict[str, float],
    tracking_uri: str | None = None,
    experiment_name: str = CSS_EXPERIMENT,
) -> str:
    """Log params, develop/holdout metrics, and pipeline.joblib; return run id."""
    uri = resolve_tracking_uri(tracking_uri)
    _prepare_file_store(uri)
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run() as run:
        mlflow.set_tag("pipeline", "credit_css")
        mlflow.set_tag("stage", "fit")
        for key, value in params.items():
            mlflow.log_param(key, value)
        for key, value in metrics.items():
            mlflow.log_metric(key, float(value))
        mlflow.log_artifact(str(artifact_path))
        return run.info.run_id
