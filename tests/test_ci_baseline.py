"""Hermetic tests for CI baseline and fixture contract."""

import hashlib
import json
from datetime import date

from smartwealthai import __version__
from smartwealthai.fixture_lake import (
    FIXTURES_DIR,
    load_fixture_fundamentals,
    load_fixture_sec_companyfacts,
    load_fixture_yfinance_history,
    point_in_time_fundamentals,
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


def test_fixture_manifest_matches_committed_files() -> None:
    manifest = json.loads((FIXTURES_DIR / "MANIFEST.json").read_text())
    expected_hashes = manifest["fixture_files_sha256"]
    actual_files = {
        path.relative_to(FIXTURES_DIR).as_posix()
        for path in FIXTURES_DIR.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }

    assert actual_files == set(expected_hashes)
    for relative_path, expected_hash in expected_hashes.items():
        file_bytes = (FIXTURES_DIR / relative_path).read_bytes()

        assert hashlib.sha256(file_bytes).hexdigest() == expected_hash


def test_point_in_time_query_returns_latest_known_version_only() -> None:
    snapshot = point_in_time_fundamentals(decision_date=date(2025, 1, 1))
    aapl_row = snapshot.loc[
        (snapshot["ticker"] == "AAPL") & (snapshot["metric"] == "OperatingIncomeLoss")
    ].iloc[0]

    assert aapl_row["as_of_date"].date().isoformat() == "2024-11-01"
    assert aapl_row["version_id"] == 1
    assert aapl_row["source_accession"] == "0000320193-24-000123"


def test_point_in_time_query_preserves_metrics_for_same_period() -> None:
    snapshot = point_in_time_fundamentals(decision_date=date(2025, 1, 1))
    aapl_metrics = set(snapshot.loc[snapshot["ticker"] == "AAPL", "metric"])

    assert {"OperatingIncomeLoss", "TotalAssets"}.issubset(aapl_metrics)


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
