"""Hermetic tests for MLflow demo pipeline run logging (issue #61)."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from mlflow import MlflowClient

from smartwealthai.magic_formula_metrics import FORMULA_VERSION
from smartwealthai.magic_formula_ranking import score_universe
from smartwealthai.mlflow_run_logging import (
    DEMO_PIPELINE_EXPERIMENT,
    _prepare_file_store,
    log_demo_pipeline_run,
    resolve_git_sha,
    resolve_tracking_uri,
    summarize_metric_distribution,
)
from smartwealthai.normalize_simfin import cli_run as normalize_cli_run
from smartwealthai.price_ingest import run_price_ingest
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)


@pytest.fixture
def tracking_uri(tmp_path: Path) -> str:
    return tmp_path.joinpath("mlruns").as_uri()


@pytest.fixture
def portfolio_parquet(tmp_path: Path) -> Path:
    path = tmp_path / "portfolio.parquet"
    pd.DataFrame(
        [
            {
                "run_date": RUN_DATE,
                "cik": "0000320193",
                "ticker": "AAPL",
                "combined_rank": 2,
                "weight": 1.0,
                "market_cap": 1_000_000.0,
            }
        ]
    ).to_parquet(path, index=False)
    return path


def _log_kwargs(
    *,
    tracking_uri: str,
    portfolio_parquet: Path,
    git_sha: str = "testsha123",
) -> dict[str, object]:
    return {
        "tracking_uri": tracking_uri,
        "run_date": RUN_DATE,
        "formula_version": FORMULA_VERSION,
        "universe_count": 5,
        "portfolio_size": 30,
        "quality_n_valid": 3,
        "quality_n_invalid": 2,
        "cheap_n_valid": 4,
        "cheap_n_invalid": 1,
        "rankable_count": 3,
        "portfolio_count": 3,
        "roc_values": [0.1, 0.2, 0.3],
        "ey_values": [0.05, 0.1, 0.15],
        "portfolio_parquet": portfolio_parquet,
        "git_sha": git_sha,
    }


@pytest.fixture
def log_kwargs(tracking_uri: str, portfolio_parquet: Path) -> dict[str, object]:
    return _log_kwargs(tracking_uri=tracking_uri, portfolio_parquet=portfolio_parquet)


def test_log_demo_pipeline_run_creates_run_with_run_date_param(
    tracking_uri: str,
    log_kwargs: dict[str, object],
) -> None:
    run_id = log_demo_pipeline_run(**log_kwargs)

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    assert run.data.params["run_date"] == RUN_DATE.isoformat()
    experiment = client.get_experiment_by_name(DEMO_PIPELINE_EXPERIMENT)
    assert experiment is not None
    assert run.info.experiment_id == experiment.experiment_id


def test_log_demo_pipeline_run_logs_quality_counts(
    tracking_uri: str,
    log_kwargs: dict[str, object],
) -> None:
    run_id = log_demo_pipeline_run(**log_kwargs)

    metrics = MlflowClient(tracking_uri=tracking_uri).get_run(run_id).data.metrics
    assert metrics["quality_n_valid"] == 3.0
    assert metrics["quality_n_invalid"] == 2.0
    assert metrics["cheap_n_valid"] == 4.0
    assert metrics["cheap_n_invalid"] == 1.0


def test_log_demo_pipeline_run_logs_roc_and_ey_quantiles(
    tracking_uri: str,
    log_kwargs: dict[str, object],
) -> None:
    run_id = log_demo_pipeline_run(**log_kwargs)

    metrics = MlflowClient(tracking_uri=tracking_uri).get_run(run_id).data.metrics
    assert metrics["roc_p50"] == pytest.approx(0.2)
    assert metrics["ey_p50"] == pytest.approx(0.1)


def test_log_demo_pipeline_run_registers_portfolio_artifact(
    tracking_uri: str,
    log_kwargs: dict[str, object],
    tmp_path: Path,
) -> None:
    run_id = log_demo_pipeline_run(**log_kwargs)

    client = MlflowClient(tracking_uri=tracking_uri)
    dest = tmp_path / "artifacts"
    dest.mkdir()
    client.download_artifacts(run_id, "", dst_path=str(dest))
    assert (dest / "portfolio.parquet").is_file()


def test_log_demo_pipeline_run_tags_git_sha(
    tracking_uri: str,
    log_kwargs: dict[str, object],
) -> None:
    run_id = log_demo_pipeline_run(**log_kwargs)

    tags = MlflowClient(tracking_uri=tracking_uri).get_run(run_id).data.tags
    assert tags["git_sha"] == "testsha123"


def test_log_demo_pipeline_run_honors_explicit_tracking_uri(
    portfolio_parquet: Path,
    tmp_path: Path,
) -> None:
    uri = tmp_path.joinpath("custom-mlruns").as_uri()
    run_id = log_demo_pipeline_run(
        **_log_kwargs(tracking_uri=uri, portfolio_parquet=portfolio_parquet),
    )

    assert MlflowClient(tracking_uri=uri).get_run(run_id).info.run_id == run_id


def test_summarize_metric_distribution_empty_returns_no_quantiles() -> None:
    assert summarize_metric_distribution([]) == {}


def test_resolve_git_sha_returns_nonempty_string() -> None:
    assert resolve_git_sha()


def test_resolve_tracking_uri_prefers_argument(tmp_path: Path) -> None:
    uri = tmp_path.joinpath("mlruns").as_uri()
    assert resolve_tracking_uri(uri) == uri


def test_resolve_tracking_uri_defaults_to_cwd_mlruns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    assert resolve_tracking_uri() == Path.cwd().joinpath("mlruns").as_uri()


def test_resolve_git_sha_returns_unknown_when_git_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr("smartwealthai.mlflow_run_logging.subprocess.run", fail_git)
    assert resolve_git_sha() == "unknown"


def test_prepare_file_store_sets_allow_for_file_uri(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("MLFLOW_ALLOW_FILE_STORE", raising=False)
    _prepare_file_store(tmp_path.joinpath("mlruns").as_uri())
    assert os.environ["MLFLOW_ALLOW_FILE_STORE"] == "true"


def test_prepare_file_store_noop_for_http_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MLFLOW_ALLOW_FILE_STORE", raising=False)
    _prepare_file_store("http://localhost:5000")
    assert "MLFLOW_ALLOW_FILE_STORE" not in os.environ


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    root = tmp_path / "lake"
    build_universe(root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    normalize_cli_run(
        [
            "--data-dir",
            str(root),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--universe-run-date",
            RUN_DATE.isoformat(),
        ]
    )
    run_price_ingest(data_dir=root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    return root


def test_score_universe_logs_mlflow_run_with_portfolio_artifact(
    lake: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracking_uri = tmp_path.joinpath("mlruns").as_uri()
    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)

    result = score_universe(lake, run_date=RUN_DATE, portfolio_size=3)

    assert result.mlflow_run_id is not None
    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(result.mlflow_run_id)
    assert run.data.params["run_date"] == RUN_DATE.isoformat()
    dest = tmp_path / "downloaded"
    dest.mkdir()
    client.download_artifacts(result.mlflow_run_id, "", dst_path=str(dest))
    assert (dest / "portfolio.parquet").is_file()
