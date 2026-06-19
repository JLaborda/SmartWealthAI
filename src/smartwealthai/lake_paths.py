"""Path builders for the local data lake raw zone.

Paths follow the layout documented in ``docs/mvp/features/etl-data-lake.md`` (Fundamentals
download spike) so local runs can move to S3 without renaming partitions.

Example::

    companyfacts_path(Path("data"), "320193", date(2026, 6, 7))
    # → data/raw/sec_edgar/cik=0000320193/endpoint=companyfacts/
    #   as_of_date=2026-06-07/response.json
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

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
