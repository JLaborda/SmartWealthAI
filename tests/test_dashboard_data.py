"""Hermetic tests for dashboard data loading (issue #62)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from smartwealthai.dashboard_data import (
    discover_latest_run_date,
    load_dashboard_snapshot,
    overview_headline,
    resolve_data_dir,
)
from smartwealthai.magic_formula_ranking import score_universe
from smartwealthai.normalize_simfin import cli_run as normalize_cli_run
from smartwealthai.price_ingest import run_price_ingest
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)


@pytest.fixture
def scored_lake(tmp_path: Path) -> Path:
    """Fixture lake with universe, fundamentals, prices, and scoring artifacts."""
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
    score_universe(root, run_date=RUN_DATE, portfolio_size=3)
    return root


def test_load_dashboard_snapshot_reads_combined_ranking_from_lake(scored_lake: Path) -> None:
    snapshot = load_dashboard_snapshot(scored_lake, run_date=RUN_DATE)

    assert snapshot.has_ranking
    assert snapshot.ranking.iloc[0]["ticker"] == "FOO"
    assert {"roc", "ey", "roc_rank", "ey_rank", "combined_rank"}.issubset(snapshot.ranking.columns)


def test_load_dashboard_snapshot_reads_portfolio_from_lake(scored_lake: Path) -> None:
    snapshot = load_dashboard_snapshot(scored_lake, run_date=RUN_DATE)

    assert snapshot.has_portfolio
    assert list(snapshot.portfolio["ticker"]) == ["FOO", "MSFT", "AAPL"]
    assert snapshot.portfolio["weight"].tolist() == pytest.approx([1 / 3, 1 / 3, 1 / 3])


def test_load_dashboard_snapshot_missing_data_returns_empty_state(tmp_path: Path) -> None:
    snapshot = load_dashboard_snapshot(tmp_path, run_date=RUN_DATE)

    assert not snapshot.has_ranking
    assert not snapshot.has_portfolio
    assert snapshot.ranking.empty
    assert snapshot.portfolio.empty


def test_discover_latest_run_date_finds_scored_partition(scored_lake: Path) -> None:
    assert discover_latest_run_date(scored_lake) == RUN_DATE


def test_overview_headline_summarizes_portfolio(scored_lake: Path) -> None:
    snapshot = load_dashboard_snapshot(scored_lake, run_date=RUN_DATE)
    headline = overview_headline(snapshot)

    assert headline.run_date == RUN_DATE
    assert headline.portfolio_count == 3
    assert headline.ranked_count == 4
    assert headline.top_ticker == "FOO"


def test_resolve_data_dir_defaults_to_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMARTWEALTHAI_DATA_DIR", raising=False)
    assert resolve_data_dir() == Path("data")


def test_resolve_data_dir_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMARTWEALTHAI_DATA_DIR", "/tmp/lake")
    assert resolve_data_dir() == Path("/tmp/lake")


def test_run_dashboard_entry_point_registered() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "smartwealthai.run_dashboard", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--data-dir" in result.stdout
