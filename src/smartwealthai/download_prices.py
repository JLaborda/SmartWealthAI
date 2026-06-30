"""CLI to build run-date prices from SimFin shareprices/latest."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.cli_lake import lake_root_options, resolve_cli_data_dir
from smartwealthai.lake_paths import price_ingest_errors_path
from smartwealthai.price_ingest import run_price_ingest

logger = logging.getLogger(__name__)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@lake_root_options
@click.option(
    "--run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Decision date (matches universe partition).",
)
@click.option(
    "--snapshot-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Raw SimFin shareprices partition date (defaults to run-date).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Rebuild curated snapshot even when it already exists.",
)
def main(
    lake_root_uri: str | None,
    data_dir: Path | None,
    run_date: datetime,
    snapshot_date: datetime | None,
    force: bool,
) -> None:
    """Build curated run-date prices from SimFin bulk shareprices/latest."""
    try:
        lake_path = resolve_cli_data_dir(lake_root_uri=lake_root_uri, data_dir=data_dir)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    decision_date = run_date.date()
    snapshot = snapshot_date.date() if snapshot_date is not None else decision_date

    try:
        ingest_run = run_price_ingest(
            data_dir=lake_path,
            run_date=decision_date,
            snapshot_date=snapshot,
            force=force,
        )
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc

    if ingest_run.run_skipped:
        click.echo(f"Skipped price ingest for {decision_date} (curated snapshot exists).")
        raise SystemExit(0)

    click.echo(f"Priced tickers: {ingest_run.included}")
    click.echo(f"Missing tickers: {len(ingest_run.missing_tickers)}")
    if ingest_run.curated_path is not None:
        click.echo(f"Wrote curated snapshot: {ingest_run.curated_path}")

    if ingest_run.missing_tickers:
        payload = [
            {"ticker": ticker, "error": "no SimFin share price on or before run_date"}
            for ticker in ingest_run.missing_tickers
        ]
        error_file = price_ingest_errors_path(lake_path, run_date=decision_date)
        error_file.parent.mkdir(parents=True, exist_ok=True)
        error_file.write_text(json.dumps(payload, indent=2))
        click.echo(f"Wrote error summary: {error_file}")
        for ticker in ingest_run.missing_tickers[:10]:
            logger.warning("Missing price: %s", ticker)
        if len(ingest_run.missing_tickers) > 10:
            logger.warning("... and %d more missing tickers", len(ingest_run.missing_tickers) - 10)

    if ingest_run.included == 0:
        raise SystemExit(1)
    raise SystemExit(0)


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
