"""Path builders for the local data lake raw zone.

Paths follow the layout documented in ``docs/mvp/features/etl-data-lake.md`` (Fundamentals
download spike) so local runs can move to S3 without renaming partitions.

Example::

    companyfacts_path(Path("data"), "320193", date(2026, 6, 7))
    # → data/raw/sec_edgar/cik=0000320193/endpoint=companyfacts/
    #   as_of_date=2026-06-07/response.json
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

_FISCAL_PERIOD_RE = re.compile(r"^\d{4}Q[1-4]$")

STATEMENT_NAMES: tuple[str, ...] = (
    "income_statement",
    "balance_sheet",
    "cashflow_statement",
)
"""edgartools statement keys written as ``{name}_annual.parquet``."""


def pad_cik(cik: str) -> str:
    """Return a 10-digit zero-padded CIK.

    Args:
        cik: Raw CIK string (may already be padded).

    Returns:
        CIK formatted as 10 digits, e.g. ``"0000320193"``.
    """
    return str(cik).zfill(10)


def is_valid_cik(cik: str) -> bool:
    """Return True if ``cik`` is a 10-digit SEC CIK after zero-padding."""
    padded = pad_cik(cik)
    return len(padded) == 10 and padded.isdigit()


def is_valid_fiscal_period(period: str) -> bool:
    """Return True if ``period`` is a safe ``YYYYQn`` partition label."""
    return bool(_FISCAL_PERIOD_RE.match(period))


def companyfacts_path(data_dir: Path, cik: str, as_of_date: date) -> Path:
    """Build the path for a verbatim SEC ``companyfacts`` JSON snapshot.

    Args:
        data_dir: Data lake root (e.g. ``Path("data")``).
        cik: SEC issuer CIK.
        as_of_date: Snapshot partition date for the download run.

    Returns:
        Target path for the raw JSON response.
    """
    return (
        data_dir
        / "raw"
        / "sec_edgar"
        / f"cik={pad_cik(cik)}"
        / "endpoint=companyfacts"
        / f"as_of_date={as_of_date.isoformat()}"
        / "response.json"
    )


def edgartools_statement_path(
    data_dir: Path,
    cik: str,
    as_of_date: date,
    statement: str,
) -> Path:
    """Build the path for an edgartools annual statement parquet file.

    Args:
        data_dir: Data lake root.
        cik: SEC issuer CIK (partition key; download uses ``ticker`` via CLI).
        as_of_date: Snapshot partition date.
        statement: One of ``STATEMENT_NAMES``.

    Returns:
        Target path for the parquet artifact.

    Raises:
        ValueError: If ``statement`` is not a known statement name.
    """
    if statement not in STATEMENT_NAMES:
        msg = f"Unknown statement: {statement}"
        raise ValueError(msg)
    return (
        data_dir
        / "raw"
        / "edgartools"
        / f"cik={pad_cik(cik)}"
        / f"as_of_date={as_of_date.isoformat()}"
        / f"{statement}_annual.parquet"
    )


def errors_path(data_dir: Path, as_of_date: date) -> Path:
    """Build the path for the per-run download error summary.

    The file is written only when one or more issuers fail during a run.
    """
    return (
        data_dir / "raw" / "download_runs" / f"as_of_date={as_of_date.isoformat()}" / "errors.json"
    )


def simfin_errors_path(data_dir: Path, as_of_date: date) -> Path:
    """Build the path for a SimFin bulk download run error summary."""
    return (
        data_dir
        / "raw"
        / "simfin"
        / "download_runs"
        / f"as_of_date={as_of_date.isoformat()}"
        / "errors.json"
    )


def simfin_source_filename(
    *,
    dataset: str,
    variant: str | None,
    market: str | None,
) -> str:
    """Return the SimFin bulk CSV filename for a dataset partition.

    Mirrors ``simfin.paths._filename_dataset`` so lake paths match verbatim
    files produced by the ``simfin`` package cache.
    """
    name = dataset if market is None else f"{market}-{dataset}"
    if variant is not None:
        name = f"{name}-{variant}"
    return f"{name}.csv"


def simfin_bulk_path(
    data_dir: Path,
    *,
    dataset: str,
    variant: str | None,
    market: str | None,
    as_of_date: date,
) -> Path:
    """Build the path for a verbatim SimFin bulk CSV snapshot.

    Layout: ``raw/simfin/dataset=<name>/variant=<v>/market=<m>/as_of_date=<date>/``.
    Datasets without a SimFin variant use ``variant=default``; datasets without a
    market keyword (e.g. ``industries``) still partition under ``market=us``.
    """
    variant_key = variant if variant is not None else "default"
    market_key = market if market is not None else "us"
    filename = simfin_source_filename(dataset=dataset, variant=variant, market=market)
    return (
        data_dir
        / "raw"
        / "simfin"
        / f"dataset={dataset}"
        / f"variant={variant_key}"
        / f"market={market_key}"
        / f"as_of_date={as_of_date.isoformat()}"
        / filename
    )


def fiscal_period_label(report_date: date) -> str:
    """Return ``YYYYQn`` partition label for a fiscal period end date."""
    quarter = (report_date.month - 1) // 3 + 1
    return f"{report_date.year}Q{quarter}"


def curated_fundamentals_path(data_dir: Path, *, cik: str, period: str) -> Path:
    """Build the path for curated fundamentals parquet for one CIK and period.

    Raises:
        ValueError: If ``cik`` or ``period`` are not safe partition keys.
    """
    if not is_valid_cik(cik):
        msg = f"Invalid CIK partition key: {cik!r}"
        raise ValueError(msg)
    if not is_valid_fiscal_period(period):
        msg = f"Invalid fiscal period partition key: {period!r}"
        raise ValueError(msg)
    return (
        data_dir
        / "curated"
        / "fundamentals"
        / f"cik={pad_cik(cik)}"
        / f"period={period}"
        / "fundamentals.parquet"
    )


def curated_issues_path(data_dir: Path, *, run_date: date) -> Path:
    """Build the path for the fundamentals review queue on a run date."""
    return (
        data_dir
        / "curated"
        / "issues"
        / f"run_date={run_date.isoformat()}"
        / "fundamentals.parquet"
    )


def curated_universe_path(data_dir: Path, *, run_date: date) -> Path:
    """Build the path for the daily investable universe snapshot."""
    return (
        data_dir / "curated" / "universe" / f"run_date={run_date.isoformat()}" / "universe.parquet"
    )


def curated_exclusions_path(data_dir: Path, *, run_date: date) -> Path:
    """Build the path for the universe exclusion log on a run date."""
    return (
        data_dir
        / "curated"
        / "universe"
        / f"run_date={run_date.isoformat()}"
        / "exclusions.parquet"
    )


def yfinance_raw_path(
    data_dir: Path,
    *,
    ticker: str,
    endpoint: str,
    as_of_date: date,
) -> Path:
    """Build the path for a verbatim yfinance response snapshot."""
    return (
        data_dir
        / "raw"
        / "yfinance"
        / f"ticker={ticker}"
        / f"endpoint={endpoint}"
        / f"as_of_date={as_of_date.isoformat()}"
        / f"{endpoint}.json"
    )


def curated_prices_path(data_dir: Path, *, ticker: str, year: int) -> Path:
    """Build the path for curated daily prices for one ticker and calendar year.

    Phase 2 full-history layout; demo uses :func:`curated_prices_snapshot_path`.
    """
    return data_dir / "curated" / "prices" / f"ticker={ticker}" / f"year={year}" / "prices.parquet"


def curated_prices_snapshot_path(data_dir: Path, *, run_date: date) -> Path:
    """Build the path for the demo cross-sectional price snapshot on ``run_date``."""
    return data_dir / "curated" / "prices" / f"run_date={run_date.isoformat()}" / "prices.parquet"


def yfinance_errors_path(data_dir: Path, *, run_date: date) -> Path:
    """Build the path for a yfinance price ingest run error summary (phase 2)."""
    return (
        data_dir
        / "raw"
        / "yfinance"
        / "download_runs"
        / f"run_date={run_date.isoformat()}"
        / "errors.json"
    )


def price_ingest_errors_path(data_dir: Path, *, run_date: date) -> Path:
    """Build the path for missing-ticker errors from SimFin price ingest."""
    return (
        data_dir
        / "curated"
        / "prices"
        / "download_runs"
        / f"run_date={run_date.isoformat()}"
        / "errors.json"
    )


def artifact_paths(data_dir: Path, cik: str, as_of_date: date) -> list[Path]:
    """Return all raw artifact paths produced for one CIK on a given date.

    One ``companyfacts`` JSON plus three edgartools statement parquets (4 total).
    """
    paths = [companyfacts_path(data_dir, cik, as_of_date)]
    paths.extend(
        edgartools_statement_path(data_dir, cik, as_of_date, statement)
        for statement in STATEMENT_NAMES
    )
    return paths
