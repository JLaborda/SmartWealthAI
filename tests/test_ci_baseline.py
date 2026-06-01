"""Hermetic tests for CI baseline and fixture contract."""

from datetime import date

import pandas as pd

import smartwealthai.fixture_lake as fixture_lake
from smartwealthai import __version__
from smartwealthai.fixture_lake import (
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


def test_point_in_time_query_returns_latest_known_version_only() -> None:
    snapshot = point_in_time_fundamentals(decision_date=date(2025, 1, 1))
    aapl_row = snapshot.loc[snapshot["ticker"] == "AAPL"].iloc[0]

    assert aapl_row["as_of_date"].date().isoformat() == "2024-11-01"
    assert aapl_row["version_id"] == 1
    assert aapl_row["source_accession"] == "0000320193-24-000123"


def test_point_in_time_query_keeps_latest_version_per_metric(monkeypatch) -> None:
    fundamentals = pd.DataFrame(
        [
            {
                "cik": "0000320193",
                "ticker": "AAPL",
                "entity_name": "Apple Inc.",
                "metric": "Revenue",
                "fiscal_period_end": pd.Timestamp("2024-09-28"),
                "as_of_date": pd.Timestamp("2024-10-31"),
                "version_id": 1,
                "form": "10-K",
                "source_accession": "revenue-v1",
                "value_usd": 391_035_000_000,
            },
            {
                "cik": "0000320193",
                "ticker": "AAPL",
                "entity_name": "Apple Inc.",
                "metric": "Revenue",
                "fiscal_period_end": pd.Timestamp("2024-09-28"),
                "as_of_date": pd.Timestamp("2024-11-15"),
                "version_id": 2,
                "form": "10-K/A",
                "source_accession": "revenue-v2",
                "value_usd": 391_100_000_000,
            },
            {
                "cik": "0000320193",
                "ticker": "AAPL",
                "entity_name": "Apple Inc.",
                "metric": "OperatingIncomeLoss",
                "fiscal_period_end": pd.Timestamp("2024-09-28"),
                "as_of_date": pd.Timestamp("2024-10-31"),
                "version_id": 1,
                "form": "10-K",
                "source_accession": "operating-income-v1",
                "value_usd": 123_216_000_000,
            },
            {
                "cik": "0000320193",
                "ticker": "AAPL",
                "entity_name": "Apple Inc.",
                "metric": "Assets",
                "fiscal_period_end": pd.Timestamp("2024-09-28"),
                "as_of_date": pd.Timestamp("2024-10-31"),
                "version_id": 1,
                "form": "10-K",
                "source_accession": "assets-v1",
                "value_usd": 364_980_000_000,
            },
        ]
    )
    monkeypatch.setattr(fixture_lake, "load_fixture_fundamentals", lambda: fundamentals)

    snapshot = fixture_lake.point_in_time_fundamentals(decision_date=date(2024, 12, 1))
    aapl_rows = snapshot.loc[snapshot["ticker"] == "AAPL"]

    assert set(aapl_rows["metric"]) == {"Assets", "OperatingIncomeLoss", "Revenue"}
    revenue = aapl_rows.loc[aapl_rows["metric"] == "Revenue"].iloc[0]
    assert revenue["version_id"] == 2
    assert revenue["source_accession"] == "revenue-v2"


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
