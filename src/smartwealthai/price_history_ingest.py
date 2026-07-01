"""Phase-2 daily price history from SimFin bulk shareprices/daily."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.download_simfin import should_skip_dataset
from smartwealthai.lake_paths import curated_prices_path, simfin_bulk_path
from smartwealthai.price_ingest import load_universe_tickers, should_skip_artifact
from smartwealthai.simfin_client import fetch_dataset_csv

CURATED_DAILY_PRICE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "price_date",
    "close",
    "adj_close",
    "volume",
)


@dataclass
class PriceHistoryIngestRun:
    """Outcome of one daily price history ingest run."""

    partitions_written: list[Path] = field(default_factory=list)
    partitions_skipped: int = 0
    row_count: int = 0


def shareprices_daily_raw_path(data_dir: Path, *, snapshot_date: date) -> Path:
    """Return the raw SimFin shareprices/daily lake path for ``snapshot_date``."""
    return simfin_bulk_path(
        data_dir,
        dataset="shareprices",
        variant="daily",
        market="us",
        as_of_date=snapshot_date,
    )


def load_raw_shareprices_daily(data_dir: Path, *, snapshot_date: date) -> pd.DataFrame:
    """Load the verbatim SimFin shareprices/daily CSV from the raw lake."""
    path = shareprices_daily_raw_path(data_dir, snapshot_date=snapshot_date)
    if not path.exists():
        msg = f"SimFin shareprices/daily not found: {path}"
        raise FileNotFoundError(msg)
    return pd.read_csv(path, sep=";")


def ensure_raw_shareprices_daily(
    data_dir: Path,
    *,
    snapshot_date: date,
    refresh_days: int,
    force: bool,
    fetch_csv: Callable[..., Path] | None = None,
) -> Path:
    """Download SimFin daily shareprices into the raw lake when missing or stale."""
    downloader = fetch_csv if fetch_csv is not None else fetch_dataset_csv
    lake_path = shareprices_daily_raw_path(data_dir, snapshot_date=snapshot_date)
    if should_skip_dataset(lake_path, refresh_days=refresh_days, force=force):
        return lake_path

    source = downloader(
        dataset="shareprices",
        variant="daily",
        market="us",
        refresh_days=0 if force else refresh_days,
    )
    lake_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, lake_path)
    return lake_path


def build_daily_price_rows(
    shareprices: pd.DataFrame,
    tickers: list[str],
    *,
    start_date: date,
    end_date: date,
) -> list[dict[str, object]]:
    """Filter SimFin daily rows to ``tickers`` and the inclusive date window."""
    if shareprices.empty or not tickers:
        return []

    ticker_set = {ticker.upper() for ticker in tickers}
    frame = shareprices.copy()
    frame["ticker"] = frame["Ticker"].astype(str).str.upper()
    frame["price_day"] = pd.to_datetime(frame["Date"]).dt.date

    eligible = frame.loc[
        frame["ticker"].isin(ticker_set)
        & (frame["price_day"] >= start_date)
        & (frame["price_day"] <= end_date)
    ]
    if eligible.empty:
        return []

    rows: list[dict[str, object]] = []
    for _, row in eligible.sort_values(["ticker", "price_day"]).iterrows():
        rows.append(
            {
                "ticker": row["ticker"],
                "price_date": row["price_day"].isoformat(),
                "close": float(row["Close"]),
                "adj_close": float(row["Adj. Close"]),
                "volume": float(row["Volume"]),
            }
        )
    return rows


def write_curated_daily_prices(
    data_dir: Path,
    rows: list[dict[str, object]],
    *,
    force: bool,
) -> tuple[list[Path], int]:
    """Write daily price rows partitioned by ticker and calendar year."""
    if not rows:
        return [], 0

    frame = pd.DataFrame(rows, columns=list(CURATED_DAILY_PRICE_COLUMNS))
    frame["price_day"] = pd.to_datetime(frame["price_date"]).dt.date
    frame["year"] = pd.to_datetime(frame["price_date"]).dt.year

    written: list[Path] = []
    skipped = 0
    for (ticker, year), group in frame.groupby(["ticker", "year"], sort=True):
        path = curated_prices_path(data_dir, ticker=str(ticker), year=int(year))
        if should_skip_artifact(path, force=force):
            skipped += 1
            continue
        partition = group.drop(columns=["price_day", "year"]).reset_index(drop=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        partition.to_parquet(path, index=False)
        written.append(path)

    return written, skipped


def _load_daily_prices_for_years(
    data_dir: Path,
    *,
    ticker: str,
    years: tuple[int, ...],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    normalized = ticker.upper()
    for year in years:
        path = curated_prices_path(data_dir, ticker=normalized, year=year)
        if path.exists():
            frames.append(pd.read_parquet(path))
    if not frames:
        return pd.DataFrame(columns=list(CURATED_DAILY_PRICE_COLUMNS))
    return pd.concat(frames, ignore_index=True)


def lookup_daily_adj_close(
    data_dir: Path,
    *,
    ticker: str,
    as_of_date: date,
) -> float:
    """Return ``adj_close`` on the latest trading day on or before ``as_of_date``."""
    # ponytail: reads at most two year partitions; upgrade path is DuckDB over curated/prices
    years = (as_of_date.year - 1, as_of_date.year)
    frame = _load_daily_prices_for_years(data_dir, ticker=ticker, years=years)
    if frame.empty:
        msg = f"No daily price history for {ticker!r}"
        raise LookupError(msg)

    work = frame.copy()
    work["price_day"] = pd.to_datetime(work["price_date"]).dt.date
    eligible = work.loc[work["price_day"] <= as_of_date]
    if eligible.empty:
        msg = f"No daily price for {ticker!r} on or before {as_of_date}"
        raise LookupError(msg)

    latest = eligible.sort_values("price_day").iloc[-1]
    return float(latest["adj_close"])


def run_price_history_ingest(
    *,
    data_dir: Path,
    tickers: list[str],
    start_date: date,
    end_date: date,
    snapshot_date: date,
    force: bool = False,
) -> PriceHistoryIngestRun:
    """Normalize SimFin shareprices/daily into curated ticker/year partitions."""
    shareprices = load_raw_shareprices_daily(data_dir, snapshot_date=snapshot_date)
    rows = build_daily_price_rows(
        shareprices,
        tickers,
        start_date=start_date,
        end_date=end_date,
    )
    written, skipped = write_curated_daily_prices(data_dir, rows, force=force)
    return PriceHistoryIngestRun(
        partitions_written=written,
        partitions_skipped=skipped,
        row_count=len(rows),
    )


def resolve_history_tickers(
    data_dir: Path,
    *,
    universe_run_date: date | None,
    explicit_tickers: tuple[str, ...],
) -> list[str]:
    """Merge universe and explicit ticker filters for price history ingest."""
    ticker_set: set[str] | None = None
    if universe_run_date is not None:
        ticker_set = {
            ticker.upper() for ticker in load_universe_tickers(data_dir, run_date=universe_run_date)
        }
    if explicit_tickers:
        explicit = {ticker.upper() for ticker in explicit_tickers}
        ticker_set = explicit if ticker_set is None else ticker_set & explicit
    if ticker_set is None:
        msg = "Pass universe_run_date or explicit_tickers to limit scope."
        raise ValueError(msg)
    return sorted(ticker_set)
