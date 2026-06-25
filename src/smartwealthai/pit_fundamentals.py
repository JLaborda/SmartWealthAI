"""Load point-in-time curated fundamentals and prices for metric scoring."""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import click
import pandas as pd

from smartwealthai.lake_paths import (
    curated_prices_snapshot_path,
    curated_universe_path,
    pad_cik,
)
from smartwealthai.magic_formula_metrics import MetricsResult, build_metrics

# ponytail: I/O-bound cap; raise if profiling shows disk saturation
_READ_WORKERS = min(8, (os.cpu_count() or 4) + 2)


class MetricsInputError(Exception):
    """Raised when curated lake inputs are missing for a ticker."""


def resolve_ticker_cik(data_dir: Path, *, ticker: str, run_date: date) -> str:
    """Resolve a ticker to padded CIK from the curated universe snapshot."""
    path = curated_universe_path(data_dir, run_date=run_date)
    if not path.exists():
        msg = f"No universe snapshot for run_date {run_date}: {path}"
        raise MetricsInputError(msg)

    universe = pd.read_parquet(path)
    normalized = ticker.upper()
    subset = universe.loc[universe["ticker"].str.upper() == normalized]
    if subset.empty:
        msg = f"Ticker {ticker!r} not in universe for run_date {run_date}"
        raise MetricsInputError(msg)
    return pad_cik(str(subset.iloc[0]["cik"]))


def _select_pit_fundamentals(frame: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    """Return the latest PIT row per CIK on or before ``as_of_date``."""
    if frame.empty:
        return frame

    work = frame.copy()
    work["_as_of"] = pd.to_datetime(work["as_of_date"])
    decision = pd.Timestamp(as_of_date)
    eligible = work.loc[work["_as_of"] <= decision]
    if eligible.empty:
        return eligible.iloc[0:0]

    if "cik" not in eligible.columns:
        return eligible.sort_values(["_as_of", "version_id"]).iloc[[-1]]

    return eligible.sort_values(["cik", "_as_of", "version_id"]).groupby("cik", sort=False).tail(1)


def load_pit_fundamentals_row(
    data_dir: Path,
    *,
    ticker: str,
    as_of_date: date,
) -> pd.Series:
    """Return the latest curated fundamentals row for ``ticker`` on ``as_of_date``."""
    cik = resolve_ticker_cik(data_dir, ticker=ticker, run_date=as_of_date)
    cik_dir = data_dir / "curated" / "fundamentals" / f"cik={cik}"
    if not cik_dir.exists():
        msg = f"No curated fundamentals for ticker {ticker!r} (cik={cik})"
        raise MetricsInputError(msg)

    rows: list[pd.Series] = []
    for path in cik_dir.glob("period=*/fundamentals.parquet"):
        frame = pd.read_parquet(path)
        if frame.empty:
            continue
        rows.append(frame.iloc[0])

    if not rows:
        msg = f"No curated fundamentals for ticker {ticker!r}"
        raise MetricsInputError(msg)

    selected = _select_pit_fundamentals(pd.DataFrame(rows), as_of_date)
    if selected.empty:
        msg = f"No PIT fundamentals for {ticker!r} on or before {as_of_date}"
        raise MetricsInputError(msg)

    return selected.iloc[0]


def load_prices_by_ticker(data_dir: Path, *, run_date: date) -> dict[str, pd.Series]:
    """Load the full price snapshot indexed by upper-case ticker."""
    path = curated_prices_snapshot_path(data_dir, run_date=run_date)
    if not path.exists():
        msg = f"Curated prices not found: {path}"
        raise MetricsInputError(msg)

    prices = pd.read_parquet(path)
    return {str(row["ticker"]).upper(): row for _, row in prices.iterrows()}


def load_ticker_price_row(
    data_dir: Path,
    *,
    ticker: str,
    run_date: date,
) -> pd.Series:
    """Return the curated price row for ``ticker`` on ``run_date``."""
    prices = load_prices_by_ticker(data_dir, run_date=run_date)
    normalized = ticker.upper()
    if normalized not in prices:
        msg = f"No curated price for {ticker!r} on run_date {run_date}"
        raise MetricsInputError(msg)
    return prices[normalized]


def _fundamentals_paths_for_ciks(data_dir: Path, ciks: set[str]) -> list[Path]:
    base = data_dir / "curated" / "fundamentals"
    paths: list[Path] = []
    for cik in ciks:
        cik_dir = base / f"cik={cik}"
        if cik_dir.exists():
            paths.extend(cik_dir.glob("period=*/fundamentals.parquet"))
    return paths


def _cik_from_partition_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("cik="):
            return pad_cik(part.removeprefix("cik="))
    msg = f"Could not resolve CIK from fundamentals path: {path}"
    raise MetricsInputError(msg)


def _read_fundamentals_partition(path: Path) -> pd.DataFrame | None:
    frame = pd.read_parquet(path)
    if frame.empty:
        return None
    row = frame.iloc[[0]].copy()
    if "cik" not in row.columns:
        row["cik"] = _cik_from_partition_path(path)
    return row


def load_pit_fundamentals_bulk(
    data_dir: Path,
    *,
    ciks: set[str],
    as_of_date: date,
    show_progress: bool = False,
) -> dict[str, pd.Series]:
    """Load one PIT fundamentals row per CIK (bulk path for universe scoring)."""
    paths = _fundamentals_paths_for_ciks(data_dir, ciks)
    if not paths:
        return {}

    frames: list[pd.DataFrame] = []
    if show_progress:
        with (
            click.progressbar(
                length=len(paths),
                label="Loading fundamentals",
                show_eta=True,
            ) as bar,
            ThreadPoolExecutor(max_workers=_READ_WORKERS) as pool,
        ):
            futures = [pool.submit(_read_fundamentals_partition, path) for path in paths]
            for future in as_completed(futures):
                frame = future.result()
                if frame is not None:
                    frames.append(frame)
                bar.update(1)
    else:
        with ThreadPoolExecutor(max_workers=_READ_WORKERS) as pool:
            for frame in pool.map(_read_fundamentals_partition, paths, chunksize=128):
                if frame is not None:
                    frames.append(frame)

    if not frames:
        return {}

    selected = _select_pit_fundamentals(pd.concat(frames, ignore_index=True), as_of_date)
    return {pad_cik(str(row["cik"])): row for _, row in selected.iterrows()}


def _build_metrics_from_rows(
    ticker: str,
    fundamentals: pd.Series,
    price: pd.Series,
) -> MetricsResult:
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


def compute_metrics_for_ticker(
    data_dir: Path,
    *,
    ticker: str,
    as_of_date: date,
) -> MetricsResult:
    """Load curated inputs and compute ROC/EY for one ticker."""
    fundamentals = load_pit_fundamentals_row(data_dir, ticker=ticker, as_of_date=as_of_date)
    price = load_ticker_price_row(data_dir, ticker=ticker, run_date=as_of_date)
    return _build_metrics_from_rows(ticker, fundamentals, price)


def _resolve_show_progress(show_progress: bool | None) -> bool:
    if show_progress is None:
        return sys.stderr.isatty()
    return show_progress


def _ticker_progress_iter(tickers: list[str], *, enabled: bool):
    if not enabled or not tickers:
        yield from tickers
        return
    with click.progressbar(
        length=len(tickers),
        label="Computing metrics",
        show_eta=True,
    ) as bar:
        for ticker in tickers:
            yield ticker
            bar.update(1)


def compute_metrics_for_tickers(
    data_dir: Path,
    *,
    tickers: list[str],
    as_of_date: date,
    cik_by_ticker: dict[str, str] | None = None,
    show_progress: bool | None = None,
) -> list[MetricsResult]:
    """Bulk-load lake inputs and compute ROC/EY for many tickers."""
    progress_enabled = _resolve_show_progress(show_progress)

    if cik_by_ticker is None:
        path = curated_universe_path(data_dir, run_date=as_of_date)
        if not path.exists():
            msg = f"No universe snapshot for run_date {as_of_date}: {path}"
            raise MetricsInputError(msg)
        universe = pd.read_parquet(path)
        cik_by_ticker = {
            str(row["ticker"]).upper(): pad_cik(str(row["cik"])) for _, row in universe.iterrows()
        }

    ciks = {cik_by_ticker[ticker] for ticker in tickers if ticker in cik_by_ticker}
    prices = load_prices_by_ticker(data_dir, run_date=as_of_date)
    fundamentals_by_cik = load_pit_fundamentals_bulk(
        data_dir,
        ciks=ciks,
        as_of_date=as_of_date,
        show_progress=progress_enabled,
    )

    results: list[MetricsResult] = []
    for ticker in _ticker_progress_iter(tickers, enabled=progress_enabled):
        cik = cik_by_ticker.get(ticker)
        if cik is None:
            continue
        fundamentals = fundamentals_by_cik.get(cik)
        if fundamentals is None:
            continue
        price = prices.get(ticker)
        if price is None:
            continue
        results.append(_build_metrics_from_rows(ticker, fundamentals, price))
    return results


def _optional_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)
