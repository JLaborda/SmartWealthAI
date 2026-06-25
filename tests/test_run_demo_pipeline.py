"""Hermetic tests for the demo pipeline orchestrator CLI."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from smartwealthai.run_demo_pipeline import cli_run, run_demo_pipeline

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    return tmp_path / "lake"


def test_run_demo_pipeline_skips_download_and_completes(lake: Path) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
        tickers=("AAPL",),
    )

    assert result.ok
    step_names = [step.name for step in result.steps]
    assert step_names == [
        "build-universe",
        "normalize-simfin",
        "download-prices",
        "compute-metrics",
    ]
    assert len(result.metrics_results) == 1
    assert result.metrics_results[0].ticker == "AAPL"
    assert result.metrics_results[0].roc is not None
    assert result.metrics_results[0].ey is not None


def test_run_demo_pipeline_without_tickers_skips_metrics(lake: Path) -> None:
    result = run_demo_pipeline(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        skip_download=True,
    )

    assert result.ok
    assert [step.name for step in result.steps] == [
        "build-universe",
        "normalize-simfin",
        "download-prices",
    ]
    assert result.metrics_results == []


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
            "--ticker",
            "AAPL",
        ]
    )

    assert exit_code == 0
