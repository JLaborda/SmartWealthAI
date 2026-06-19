"""Demo price snapshot from SimFin bulk shareprices (latest variant)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.lake_paths import (
    curated_prices_snapshot_path,
    curated_universe_path,
    simfin_bulk_path,
)

CURATED_PRICE_COLUMNS: tuple[str, ...] = (
    "run_date",
    "ticker",
    "price_date",
    "close",
    "adj_close",
    "volume",
)


@dataclass
class PriceIngestRun:
    """Outcome of one demo price ingest run."""

    curated_path: Path | None = None
    run_skipped: bool = False
    included: int = 0
    missing_tickers: list[str] = field(default_factory=list)


def should_skip_artifact(path: Path, *, force: bool) -> bool:
    """Return True when an existing lake artifact should be reused."""
    return not force and path.exists()


def load_universe_tickers(data_dir: Path, *, run_date: date) -> list[str]:
    """Read ticker symbols from the curated universe snapshot for ``run_date``."""
    path = curated_universe_path(data_dir, run_date=run_date)
    if not path.exists():
        msg = f"Universe not found: {path}"
        raise FileNotFoundError(msg)
    universe = pd.read_parquet(path)
    return universe["ticker"].astype(str).tolist()


def shareprices_raw_path(data_dir: Path, *, snapshot_date: date) -> Path:
    """Return the raw SimFin shareprices/latest lake path for ``snapshot_date``."""
    return simfin_bulk_path(
        data_dir,
        dataset="shareprices",
        variant="latest",
        market="us",
        as_of_date=snapshot_date,
    )


def load_raw_shareprices(data_dir: Path, *, snapshot_date: date) -> pd.DataFrame:
    """Load the verbatim SimFin shareprices/latest CSV from the raw lake."""
    path = shareprices_raw_path(data_dir, snapshot_date=snapshot_date)
    if not path.exists():
        msg = f"SimFin shareprices not found: {path}"
        raise FileNotFoundError(msg)
    return pd.read_csv(path, sep=";")


def build_price_rows(
    shareprices: pd.DataFrame,
    tickers: list[str],
    *,
    run_date: date,
) -> tuple[list[dict[str, object]], list[str]]:
    """Select the latest SimFin price on or before ``run_date`` for each ticker."""
    frame = shareprices.copy()
    frame["price_day"] = pd.to_datetime(frame["Date"]).dt.date
    eligible = frame.loc[frame["price_day"] <= run_date]
    if eligible.empty:
        return [], list(tickers)

    latest = (
        eligible.sort_values(["Ticker", "price_day"])
        .groupby("Ticker", as_index=False)
        .tail(1)
        .set_index("Ticker")
    )

    rows: list[dict[str, object]] = []
    missing: list[str] = []
    for ticker in tickers:
        if ticker not in latest.index:
            missing.append(ticker)
            continue
        row = latest.loc[ticker]
        price_day = row["price_day"]
        rows.append(
            {
                "run_date": run_date.isoformat(),
                "ticker": ticker,
                "price_date": price_day.isoformat(),
                "close": float(row["Close"]),
                "adj_close": float(row["Adj. Close"]),
                "volume": float(row["Volume"]),
            }
        )
    return rows, missing


def write_curated_prices_snapshot(
    data_dir: Path,
    *,
    run_date: date,
    rows: list[dict[str, object]],
) -> Path:
    """Write the cross-sectional curated price snapshot for ``run_date``."""
    frame = pd.DataFrame(rows, columns=list(CURATED_PRICE_COLUMNS))
    path = curated_prices_snapshot_path(data_dir, run_date=run_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def run_price_ingest(
    *,
    data_dir: Path,
    run_date: date,
    snapshot_date: date | None = None,
    force: bool = False,
) -> PriceIngestRun:
    """Build run-date prices for universe tickers from SimFin shareprices/latest."""
    curated_path = curated_prices_snapshot_path(data_dir, run_date=run_date)
    if should_skip_artifact(curated_path, force=force):
        return PriceIngestRun(curated_path=curated_path, run_skipped=True)

    snapshot = snapshot_date or run_date
    tickers = load_universe_tickers(data_dir, run_date=run_date)
    shareprices = load_raw_shareprices(data_dir, snapshot_date=snapshot)
    rows, missing = build_price_rows(shareprices, tickers, run_date=run_date)

    written_path: Path | None = None
    if rows:
        written_path = write_curated_prices_snapshot(data_dir, run_date=run_date, rows=rows)

    return PriceIngestRun(
        curated_path=written_path,
        included=len(rows),
        missing_tickers=missing,
    )
