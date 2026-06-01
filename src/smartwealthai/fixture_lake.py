"""Helpers for deterministic, local fixture lake datasets."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "lake"


def load_fixture_fundamentals() -> pd.DataFrame:
    """Load fixture fundamentals used in hermetic tests."""
    return pd.read_csv(
        FIXTURES_DIR / "curated" / "fundamentals.csv",
        dtype={"cik": "string"},
        parse_dates=["fiscal_period_end", "as_of_date"],
    )


def load_fixture_sec_companyfacts(cik: str) -> dict:
    """Load reduced SEC companyfacts fixture for a given CIK."""
    path = (
        FIXTURES_DIR
        / "raw"
        / "sec_edgar"
        / f"cik={cik}"
        / "endpoint=companyfacts"
        / "as_of_date=2026-05-21"
        / "response.json"
    )
    return json.loads(path.read_text())


def load_fixture_yfinance_history(ticker: str) -> dict:
    """Load reduced yfinance history fixture for a given ticker."""
    path = (
        FIXTURES_DIR
        / "raw"
        / "yfinance"
        / f"ticker={ticker}"
        / "endpoint=history"
        / "as_of_date=2026-05-21"
        / "history.json"
    )
    return json.loads(path.read_text())


def point_in_time_fundamentals(decision_date: date) -> pd.DataFrame:
    """Return latest known fundamentals per company-period-metric as of ``decision_date``."""
    fundamentals = load_fixture_fundamentals()
    decision_ts = pd.Timestamp(decision_date)
    eligible = fundamentals.loc[fundamentals["as_of_date"] <= decision_ts].copy()

    latest = (
        eligible.sort_values(["cik", "fiscal_period_end", "metric", "as_of_date", "version_id"])
        .groupby(["cik", "fiscal_period_end", "metric"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    return latest
