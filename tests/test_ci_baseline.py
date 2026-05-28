"""Hermetic tests for CI baseline and fixture contract."""

import subprocess
from datetime import date
from pathlib import Path

from smartwealthai import __version__
from smartwealthai.fixture_lake import (
    load_fixture_fundamentals,
    load_fixture_sec_companyfacts,
    load_fixture_yfinance_history,
    point_in_time_fundamentals,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def git_ignores(path: str) -> bool:
    """Return whether Git ignore rules hide a repository-relative path."""
    return (
        subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
        == 0
    )


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"


def test_fixture_fundamentals_expose_pit_columns() -> None:
    fundamentals = load_fixture_fundamentals()

    assert len(fundamentals) > 0
    assert {
        "cik",
        "ticker",
        "metric",
        "fiscal_period_end",
        "as_of_date",
        "version_id",
        "source_accession",
        "value_usd",
    }.issubset(fundamentals.columns)


def test_point_in_time_query_returns_latest_known_version_only() -> None:
    snapshot = point_in_time_fundamentals(decision_date=date(2025, 1, 1))
    aapl_row = snapshot.loc[snapshot["ticker"] == "AAPL"].iloc[0]

    assert aapl_row["as_of_date"].date().isoformat() == "2024-11-01"
    assert aapl_row["version_id"] == 1
    assert aapl_row["source_accession"] == "0000320193-24-000123"


def test_sec_raw_fixture_contains_real_operating_income_series() -> None:
    sec_fixture = load_fixture_sec_companyfacts(cik="0000320193")

    assert sec_fixture["entityName"] == "Apple Inc."
    assert sec_fixture["metric"] == "OperatingIncomeLoss"
    assert "USD" in sec_fixture["units"]
    assert len(sec_fixture["units"]["USD"]) > 10


def test_yfinance_raw_fixture_contains_history_rows() -> None:
    yf_fixture = load_fixture_yfinance_history(ticker="AAPL")

    assert yf_fixture["ticker"] == "AAPL"
    assert len(yf_fixture["rows"]) == 10
    assert {"Date", "Close", "Volume"}.issubset(yf_fixture["rows"][0].keys())


def test_gitignore_keeps_canonical_reference_and_portfolio_paths_trackable() -> None:
    """Guard against silent omission of future MVP reference data and portfolio code."""
    trackable_paths = [
        "data/reference/ticker_mapping.csv",
        "data/reference/sp500_constituents.csv",
        "src/smartwealthai/portfolio_construction.py",
        "tests/test_portfolio_construction.py",
        "docs/mvp/features/portfolio-construction.md",
    ]
    ignored_private_paths = [
        "data/raw/sec_edgar/private-response.json",
        "data/clean/personal_finance/operations/my_operations_eur.csv",
        "data/cache/yfinance/AAPL/history.parquet",
        "my_portfolio_export.csv",
    ]

    assert not any(git_ignores(path) for path in trackable_paths)
    assert all(git_ignores(path) for path in ignored_private_paths)
