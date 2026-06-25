"""Load point-in-time curated fundamentals and prices for metric scoring."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.lake_paths import curated_prices_snapshot_path
from smartwealthai.magic_formula_metrics import MetricsResult, build_metrics


class MetricsInputError(Exception):
    """Raised when curated lake inputs are missing for a ticker."""


def load_pit_fundamentals_row(
    data_dir: Path,
    *,
    ticker: str,
    as_of_date: date,
) -> pd.Series:
    """Return the latest curated fundamentals row for ``ticker`` on ``as_of_date``."""
    fundamentals_dir = data_dir / "curated" / "fundamentals"
    if not fundamentals_dir.exists():
        msg = f"Curated fundamentals not found under {fundamentals_dir}"
        raise MetricsInputError(msg)

    rows: list[pd.Series] = []
    for path in fundamentals_dir.rglob("fundamentals.parquet"):
        frame = pd.read_parquet(path)
        if frame.empty or frame.iloc[0]["ticker"] != ticker:
            continue
        rows.append(frame.iloc[0])

    if not rows:
        msg = f"No curated fundamentals for ticker {ticker!r}"
        raise MetricsInputError(msg)

    frame = pd.DataFrame(rows)
    decision = pd.Timestamp(as_of_date)
    frame["_as_of"] = pd.to_datetime(frame["as_of_date"])
    eligible = frame.loc[frame["_as_of"] <= decision]
    if eligible.empty:
        msg = f"No PIT fundamentals for {ticker!r} on or before {as_of_date}"
        raise MetricsInputError(msg)

    latest = eligible.sort_values(["_as_of", "version_id"]).iloc[-1]
    return latest


def load_ticker_price_row(
    data_dir: Path,
    *,
    ticker: str,
    run_date: date,
) -> pd.Series:
    """Return the curated price row for ``ticker`` on ``run_date``."""
    path = curated_prices_snapshot_path(data_dir, run_date=run_date)
    if not path.exists():
        msg = f"Curated prices not found: {path}"
        raise MetricsInputError(msg)

    prices = pd.read_parquet(path)
    subset = prices.loc[prices["ticker"] == ticker]
    if subset.empty:
        msg = f"No curated price for {ticker!r} on run_date {run_date}"
        raise MetricsInputError(msg)
    return subset.iloc[0]


def compute_metrics_for_ticker(
    data_dir: Path,
    *,
    ticker: str,
    as_of_date: date,
) -> MetricsResult:
    """Load curated inputs and compute ROC/EY for one ticker."""
    fundamentals = load_pit_fundamentals_row(data_dir, ticker=ticker, as_of_date=as_of_date)
    price = load_ticker_price_row(data_dir, ticker=ticker, run_date=as_of_date)

    return build_metrics(
        ticker=ticker,
        ebit=_optional_float(fundamentals.get("ebit")),
        current_assets=_optional_float(fundamentals.get("current_assets")),
        current_liabilities=_optional_float(fundamentals.get("current_liabilities")),
        cash=_optional_float(fundamentals.get("cash")),
        short_term_debt=_optional_float(fundamentals.get("short_term_debt")),
        net_fixed_assets=_optional_float(fundamentals.get("ppe_net")),
        shares_outstanding=_optional_float(fundamentals.get("shares_outstanding")),
        adj_close=_optional_float(price.get("adj_close")),
        long_term_debt=_optional_float(fundamentals.get("long_term_debt")),
        preferred_equity=_optional_float(fundamentals.get("preferred_equity")),
        minority_interest=_optional_float(fundamentals.get("minority_interest")),
    )


def _optional_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)
