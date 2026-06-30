"""CLI to download raw SEC companyfacts and edgartools statements for a universe.

Orchestrates the fundamentals download spike documented in
``docs/mvp/features/etl-data-lake.md``. For each ``(ticker, cik)`` in the universe:

1. SEC REST — verbatim ``companyfacts`` JSON.
2. edgartools — annual income, balance, and cash-flow statements as parquet.

Usage::

    export SEC_IDENTITY="Your Name your@email.com"
    poetry run download-fundamentals --universe dow30

See ``docs/mvp/guides/download-fundamentals.md`` for the full operator guide.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import click

from smartwealthai.cli_lake import lake_root_options, resolve_cli_data_dir
from smartwealthai.edgartools_client import EdgartoolsClientError, download_statements
from smartwealthai.lake_paths import (
    STATEMENT_NAMES,
    companyfacts_path,
    edgartools_statement_path,
    errors_path,
)
from smartwealthai.sec_client import SecClientError, fetch_companyfacts
from smartwealthai.universe import UniverseEntry, load_universe

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Per-issuer outcome for one download run."""

    ticker: str
    cik: str
    downloaded: int = 0
    skipped: int = 0
    failed: bool = False
    error: str | None = None


def should_skip(path: Path, *, force: bool) -> bool:
    """Return True when an existing artifact can be reused without a network call."""
    return path.exists() and not force


def download_entry(
    entry: UniverseEntry,
    *,
    data_dir: Path,
    as_of_date: date,
    periods: int,
    force: bool,
) -> DownloadResult:
    """Download all raw artifacts for one universe entry.

    Produces up to four files under ``data_dir/raw/`` (see :mod:`smartwealthai.lake_paths`).
    Failures are captured in the result rather than raised, so the CLI can continue with
    the remaining issuers.

    Args:
        entry: Ticker and CIK from the universe CSV.
        data_dir: Local data lake root.
        as_of_date: Snapshot partition date.
        periods: Annual periods for edgartools statements.
        force: Re-download even when today's files exist.

    Returns:
        :class:`DownloadResult` with per-artifact download/skip counts or failure details.
    """
    result = DownloadResult(ticker=entry.ticker, cik=entry.cik)
    facts_path = companyfacts_path(data_dir, entry.cik, as_of_date)
    statement_paths = {
        statement: edgartools_statement_path(data_dir, entry.cik, as_of_date, statement)
        for statement in STATEMENT_NAMES
    }

    try:
        if should_skip(facts_path, force=force):
            result.skipped += 1
        else:
            fetch_companyfacts(entry.cik, facts_path, force=force)
            result.downloaded += 1

        skipped_statements = download_statements(
            entry.ticker,
            statement_paths,
            periods=periods,
            force=force,
        )
        result.skipped += len(skipped_statements)
        result.downloaded += len(STATEMENT_NAMES) - len(skipped_statements)
    except (SecClientError, EdgartoolsClientError, OSError, ValueError) as exc:
        result.failed = True
        result.error = str(exc)
    return result


def run_download(
    *,
    universe: str | None,
    universe_file: Path | None,
    data_dir: Path,
    periods: int,
    as_of_date: date | None,
    force: bool,
) -> int:
    """Execute a download run.

    Args:
        universe: Preset name (e.g. ``dow30``).
        universe_file: Explicit universe CSV path.
        data_dir: Local data lake root.
        periods: Annual periods for edgartools statements.
        as_of_date: Snapshot partition date (default: UTC today).
        force: Re-download even when today's partition exists.

    Returns:
        ``0`` when all issuers succeed, ``1`` when any issuer fails.
    """
    snapshot_date = as_of_date or datetime.now(UTC).date()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    entries = load_universe(universe, universe_file)
    results: list[DownloadResult] = []

    for entry in entries:
        logger.info("Processing %s (CIK %s)", entry.ticker, entry.cik)
        result = download_entry(
            entry,
            data_dir=data_dir,
            as_of_date=snapshot_date,
            periods=periods,
            force=force,
        )
        results.append(result)
        if result.failed:
            logger.error("Failed %s: %s", entry.ticker, result.error)
        else:
            logger.info(
                "Finished %s: downloaded=%s skipped=%s",
                entry.ticker,
                result.downloaded,
                result.skipped,
            )

    downloaded_total = sum(result.downloaded for result in results)
    skipped_total = sum(result.skipped for result in results)
    failures = [result for result in results if result.failed]

    click.echo(f"Downloaded artifacts: {downloaded_total}")
    click.echo(f"Skipped artifacts: {skipped_total}")
    click.echo(f"Failed issuers: {len(failures)}/{len(results)}")

    if failures:
        payload = [
            {
                "ticker": result.ticker,
                "cik": result.cik,
                "error": result.error,
            }
            for result in failures
        ]
        error_file = errors_path(data_dir, snapshot_date)
        error_file.parent.mkdir(parents=True, exist_ok=True)
        error_file.write_text(json.dumps(payload, indent=2))
        click.echo(f"Wrote error summary: {error_file}")
        return 1
    return 0


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog="Guide: docs/mvp/guides/download-fundamentals.md",
)
@click.option("--universe", help="Universe preset name (e.g. dow30).")
@click.option(
    "--universe-file",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Path to a universe CSV with columns ticker,cik.",
)
@lake_root_options
@click.option(
    "--periods",
    type=int,
    default=16,
    show_default=True,
    help="Number of annual periods to request from edgartools.",
)
@click.option(
    "--as-of-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Snapshot partition date (default: UTC today).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-download files even when today's partition already exists.",
)
def main(
    universe: str | None,
    universe_file: Path | None,
    lake_root_uri: str | None,
    data_dir: Path | None,
    periods: int,
    as_of_date: datetime | None,
    force: bool,
) -> None:
    """Download SEC companyfacts and edgartools annual statements for a universe."""
    try:
        lake_path = resolve_cli_data_dir(lake_root_uri=lake_root_uri, data_dir=data_dir)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    snapshot_date = as_of_date.date() if as_of_date is not None else None
    raise SystemExit(
        run_download(
            universe=universe,
            universe_file=universe_file,
            data_dir=lake_path,
            periods=periods,
            as_of_date=snapshot_date,
            force=force,
        )
    )


def run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests).

    Args:
        argv: Optional argument list (without the program name).

    Returns:
        Process exit code from :func:`run_download`.
    """
    runner = click.testing.CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
