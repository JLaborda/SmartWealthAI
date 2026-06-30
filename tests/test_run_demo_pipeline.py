"""Hermetic tests for the demo pipeline orchestrator CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from smartwealthai.lake_paths import curated_portfolio_path
from smartwealthai.magic_formula_ranking import ScoringResult
from smartwealthai.price_ingest import PriceIngestRun
from smartwealthai.run_demo_pipeline import (
    PipelineResult,
    PipelineStepResult,
    cli_run,
    format_pipeline_summary,
    main,
    run_demo_pipeline,
)

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    return tmp_path / "lake"


def test_pipeline_result_ok_false_when_step_failed() -> None:
    result = PipelineResult(
        run_date=RUN_DATE,
        steps=[PipelineStepResult("download-simfin", False, 0.1, "exit 1")],
    )

    assert not result.ok


def test_pipeline_result_ok_false_when_scoring_step_failed() -> None:
    result = PipelineResult(
        run_date=RUN_DATE,
        steps=[PipelineStepResult("score-universe", False, 0.1, "scoring failed")],
    )

    assert not result.ok


@patch("smartwealthai.run_demo_pipeline.run_download", return_value=0)
def test_run_demo_pipeline_runs_download_when_not_skipped(
    mock_download: object,
    lake: Path,
) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=False,
    )

    assert mock_download.called  # type: ignore[attr-defined]
    assert result.steps[0].name == "download-simfin"
    assert result.steps[0].ok


@patch("smartwealthai.run_demo_pipeline.run_download", return_value=1)
def test_run_demo_pipeline_aborts_on_download_failure(
    mock_download: object,
    lake: Path,
) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=False,
    )

    assert not result.ok
    assert len(result.steps) == 1
    assert result.steps[0].name == "download-simfin"


@patch(
    "smartwealthai.run_demo_pipeline.run_price_ingest",
    side_effect=FileNotFoundError("shareprices missing"),
)
def test_run_demo_pipeline_aborts_on_price_ingest_error(
    mock_ingest: object,
    lake: Path,
) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
    )

    assert not result.ok
    assert result.steps[-1].name == "download-prices"
    assert result.steps[-1].ok is False


@patch(
    "smartwealthai.run_demo_pipeline.run_price_ingest",
    return_value=PriceIngestRun(included=0, run_skipped=False),
)
def test_run_demo_pipeline_aborts_when_no_prices(
    mock_ingest: object,
    lake: Path,
) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
    )

    assert not result.ok
    assert result.steps[-1].name == "download-prices"


def test_run_demo_pipeline_limits_normalize_to_requested_tickers(lake: Path) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
        skip_mlflow=True,
        tickers=("AAPL",),
    )

    assert result.ok
    normalize_step = next(step for step in result.steps if step.name == "normalize-simfin")
    assert "1 tickers" in normalize_step.detail


def test_format_pipeline_summary_includes_scoring_artifacts(tmp_path: Path) -> None:
    portfolio_path = tmp_path / "portfolio.parquet"
    portfolio_path.touch()
    scoring = ScoringResult(
        run_date=RUN_DATE,
        quality_path=tmp_path / "quality.parquet",
        cheap_path=tmp_path / "cheap.parquet",
        combined_path=tmp_path / "combined.parquet",
        portfolio_path=portfolio_path,
        quality_issues_path=tmp_path / "quality_issues.parquet",
        cheap_issues_path=tmp_path / "cheap_issues.parquet",
        rankable_count=3,
        portfolio_count=3,
        mlflow_run_id="abc123",
    )
    result = PipelineResult(
        run_date=RUN_DATE,
        steps=[PipelineStepResult("score-universe", True, 0.2, "3 rankable, 3 in portfolio")],
        scoring=scoring,
    )

    summary = format_pipeline_summary(result)

    assert "Artifacts:" in summary
    assert str(portfolio_path) in summary
    assert "MLflow run id: abc123" in summary


def test_run_demo_pipeline_skips_download_and_completes(lake: Path) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
        skip_mlflow=True,
        tickers=("AAPL",),
    )

    assert result.ok
    step_names = [step.name for step in result.steps]
    assert step_names == [
        "build-universe",
        "normalize-simfin",
        "download-prices",
        "score-universe",
    ]
    assert result.scoring is not None
    assert result.scoring.portfolio_count >= 0


def test_run_demo_pipeline_scores_universe_and_writes_portfolio(lake: Path) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
        skip_mlflow=True,
    )

    assert result.ok
    assert result.scoring is not None
    assert any(step.name == "score-universe" and step.ok for step in result.steps)
    assert curated_portfolio_path(lake, run_date=RUN_DATE).exists()
    assert result.scoring.portfolio_count > 0


@patch("smartwealthai.run_demo_pipeline.run_download", return_value=1)
def test_cli_run_exits_nonzero_on_pipeline_failure(
    mock_download: object,
    lake: Path,
) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
        ]
    )

    assert exit_code == 1


def test_cli_main_handles_click_exception(lake: Path) -> None:
    runner = CliRunner()
    with patch(
        "smartwealthai.run_demo_pipeline.run_demo_pipeline",
        side_effect=click.ClickException("pipeline scope error"),
    ):
        result = runner.invoke(
            main,
            [
                "--data-dir",
                str(lake),
                "--run-date",
                RUN_DATE.isoformat(),
            ],
        )

    assert result.exit_code == 1
    assert "pipeline scope error" in result.output


def test_cli_run_demo_pipeline_with_fixture_lake(lake: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--skip-download",
            "--skip-mlflow",
        ]
    )

    assert exit_code == 0


def test_run_demo_pipeline_module_main_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "smartwealthai.run_demo_pipeline", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--run-date" in result.stdout
