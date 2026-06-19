"""CLI to download SimFin bulk US fundamentals into the raw data lake.

Orchestrates the demo SimFin connector documented in
``docs/mvp/features/etl-data-lake.md``. Downloads ``companies``, ``industries``,
``income`` (TTM), ``balance`` (quarterly), and ``cashflow`` (TTM) for ``market=us``.

Usage::

    export SIMFIN_API_KEY="<from secrets>"
    poetry run download-simfin

See ``docs/mvp/guides/download-simfin.md`` for the operator guide.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.lake_paths import simfin_bulk_path, simfin_errors_path
from smartwealthai.simfin_client import configure_simfin, fetch_dataset_csv

logger = logging.getLogger(__name__)

FetchCsvFn = Callable[..., Path]


def should_skip_dataset(
    path: Path,
    *,
    refresh_days: int,
    force: bool,
    now: float | None = None,
) -> bool:
    """Return True when an existing lake artifact is fresh enough to reuse."""
    if force or not path.exists():
        return False
    current = now if now is not None else time.time()
    age_days = (current - path.stat().st_mtime) / 86400
    return age_days < refresh_days


@dataclass(frozen=True)
class SimFinDatasetSpec:
    """One SimFin bulk dataset in the demo connector."""

    name: str
    variant: str | None
    market: str | None
    critical: bool = True


@dataclass
class DatasetResult:
    """Per-dataset outcome for one SimFin bulk download run."""

    name: str
    downloaded: bool = False
    skipped: bool = False
    failed: bool = False
    error: str | None = None


DEMO_DATASETS: tuple[SimFinDatasetSpec, ...] = (
    SimFinDatasetSpec("companies", variant=None, market="us"),
    SimFinDatasetSpec("industries", variant=None, market=None),
    SimFinDatasetSpec("income", variant="ttm", market="us"),
    SimFinDatasetSpec("balance", variant="quarterly", market="us"),
    SimFinDatasetSpec("cashflow", variant="ttm", market="us", critical=False),
)


def download_dataset(
    spec: SimFinDatasetSpec,
    *,
    data_dir: Path,
    as_of_date: date,
    refresh_days: int,
    force: bool,
    fetch_csv: FetchCsvFn,
    now: float | None = None,
) -> DatasetResult:
    """Download one SimFin dataset into the raw lake when needed."""
    lake_path = simfin_bulk_path(
        data_dir,
        dataset=spec.name,
        variant=spec.variant,
        market=spec.market,
        as_of_date=as_of_date,
    )
    if should_skip_dataset(lake_path, refresh_days=refresh_days, force=force, now=now):
        return DatasetResult(name=spec.name, skipped=True)

    try:
        source = fetch_csv(
            dataset=spec.name,
            variant=spec.variant,
            market=spec.market,
            refresh_days=0 if force else refresh_days,
        )
        lake_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, lake_path)
    except OSError as exc:
        return DatasetResult(name=spec.name, failed=True, error=str(exc))
    return DatasetResult(name=spec.name, downloaded=True)


def run_download(
    *,
    data_dir: Path,
    as_of_date: date,
    refresh_days: int,
    force: bool,
    api_key: str | None = None,
    cache_dir: Path | None = None,
    fetch_csv: FetchCsvFn | None = None,
) -> int:
    """Execute a SimFin bulk download run."""
    key = api_key if api_key is not None else os.environ.get("SIMFIN_API_KEY")
    if not key:
        click.echo("SIMFIN_API_KEY is not set", err=True)
        return 1

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    simfin_cache = cache_dir or (data_dir / "cache" / "simfin")
    if fetch_csv is None:
        configure_simfin(api_key=key, cache_dir=simfin_cache)
        fetch_csv = fetch_dataset_csv

    results: list[DatasetResult] = []
    for spec in DEMO_DATASETS:
        logger.info("Processing SimFin dataset %s", spec.name)
        result = download_dataset(
            spec,
            data_dir=data_dir,
            as_of_date=as_of_date,
            refresh_days=refresh_days,
            force=force,
            fetch_csv=fetch_csv,
        )
        results.append(result)
        if result.failed:
            logger.error("Failed %s: %s", spec.name, result.error)
        elif result.skipped:
            logger.info("Skipped %s (fresh lake copy)", spec.name)
        else:
            logger.info("Downloaded %s", spec.name)

    downloaded_total = sum(result.downloaded for result in results)
    skipped_total = sum(result.skipped for result in results)
    failures = [result for result in results if result.failed]
    critical_specs = {spec.name: spec for spec in DEMO_DATASETS}
    critical_failures = [result for result in failures if critical_specs[result.name].critical]

    click.echo(f"Downloaded datasets: {downloaded_total}")
    click.echo(f"Skipped datasets: {skipped_total}")
    click.echo(f"Failed datasets: {len(failures)}/{len(results)}")

    if failures:
        payload = [{"dataset": result.name, "error": result.error} for result in failures]
        error_file = simfin_errors_path(data_dir, as_of_date)
        error_file.parent.mkdir(parents=True, exist_ok=True)
        error_file.write_text(json.dumps(payload, indent=2))
        click.echo(f"Wrote error summary: {error_file}")

    if len(critical_failures) == len([spec for spec in DEMO_DATASETS if spec.critical]):
        return 1
    return 0


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data"),
    show_default=True,
    help="Data lake root.",
)
@click.option(
    "--as-of-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Snapshot partition date (default: UTC today).",
)
@click.option(
    "--refresh-days",
    type=int,
    default=7,
    show_default=True,
    help="Skip download when the on-disk lake copy is younger than this many days.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-download and overwrite lake copies regardless of age.",
)
def main(
    data_dir: Path,
    as_of_date: datetime | None,
    refresh_days: int,
    force: bool,
) -> None:
    """Download SimFin bulk US fundamentals into the raw lake."""
    snapshot_date = as_of_date.date() if as_of_date is not None else datetime.now(UTC).date()
    raise SystemExit(
        run_download(
            data_dir=data_dir,
            as_of_date=snapshot_date,
            refresh_days=refresh_days,
            force=force,
        )
    )


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
