"""CLI to ingest SimFin shareprices/daily into curated ticker/year partitions."""

from __future__ import annotations

import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.price_history_ingest import (
    ensure_raw_shareprices_daily,
    resolve_history_tickers,
    run_price_history_ingest,
)
from smartwealthai.simfin_client import configure_simfin

logger = logging.getLogger(__name__)


def resolve_tickers(
    data_dir: Path,
    *,
    universe_run_date: date | None,
    explicit_tickers: tuple[str, ...],
) -> list[str]:
    """Resolve ticker scope from CLI flags."""
    try:
        return resolve_history_tickers(
            data_dir,
            universe_run_date=universe_run_date,
            explicit_tickers=explicit_tickers,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data"),
    show_default=True,
    help="Data lake root.",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Inclusive start of the curated price window.",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Inclusive end of the curated price window.",
)
@click.option(
    "--snapshot-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: datetime.now(tz=UTC).strftime("%Y-%m-%d"),
    show_default="today (UTC)",
    help="Raw SimFin shareprices/daily partition date.",
)
@click.option(
    "--universe-run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Limit to tickers in this curated universe snapshot.",
)
@click.option(
    "--ticker",
    "tickers",
    multiple=True,
    help="Limit to specific tickers (repeatable; intersects universe when both set).",
)
@click.option(
    "--refresh-days",
    type=int,
    default=7,
    show_default=True,
    help="Skip SimFin re-download when the raw partition is newer than this.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-download raw daily shareprices and overwrite curated partitions.",
)
@click.option(
    "--skip-download",
    is_flag=True,
    help="Use existing raw shareprices/daily only (for tests and offline runs).",
)
def main(
    data_dir: Path,
    start_date: datetime,
    end_date: datetime,
    snapshot_date: datetime,
    universe_run_date: datetime | None,
    tickers: tuple[str, ...],
    refresh_days: int,
    force: bool,
    skip_download: bool,
) -> None:
    """Populate curated daily prices from SimFin bulk shareprices/daily."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    window_start = start_date.date()
    window_end = end_date.date()
    if window_start > window_end:
        raise click.ClickException("--start-date must be on or before --end-date.")

    snapshot = snapshot_date.date()
    universe_date = universe_run_date.date() if universe_run_date is not None else None
    ticker_list = resolve_tickers(
        data_dir,
        universe_run_date=universe_date,
        explicit_tickers=tickers,
    )

    if not skip_download:
        api_key = os.environ.get("SIMFIN_API_KEY")
        if not api_key:
            raise click.ClickException("SIMFIN_API_KEY is not set")
        configure_simfin(api_key=api_key, cache_dir=data_dir / "cache" / "simfin")
        try:
            raw_path = ensure_raw_shareprices_daily(
                data_dir,
                snapshot_date=snapshot,
                refresh_days=refresh_days,
                force=force,
            )
        except OSError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Raw daily shareprices: {raw_path}")

    try:
        ingest_run = run_price_history_ingest(
            data_dir=data_dir,
            tickers=ticker_list,
            start_date=window_start,
            end_date=window_end,
            snapshot_date=snapshot,
            force=force,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Tickers: {len(ticker_list)}")
    click.echo(f"Rows normalized: {ingest_run.row_count}")
    click.echo(f"Partitions written: {len(ingest_run.partitions_written)}")
    click.echo(f"Partitions skipped: {ingest_run.partitions_skipped}")
    for path in ingest_run.partitions_written[:10]:
        click.echo(f"  {path}")
    if len(ingest_run.partitions_written) > 10:
        logger.warning("... and %d more partitions", len(ingest_run.partitions_written) - 10)

    if ingest_run.row_count == 0:
        raise SystemExit(1)
    raise SystemExit(0)


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
