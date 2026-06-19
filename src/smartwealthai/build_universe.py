"""CLI to build the demo investable universe from SimFin raw lake snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.simfin_industry_exclusions import REFERENCE_PATH
from smartwealthai.universe_builder import build_universe


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data"),
    show_default=True,
    help="Data lake root.",
)
@click.option(
    "--run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Decision date for the universe snapshot.",
)
@click.option(
    "--snapshot-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Raw SimFin companies partition date (defaults to run-date).",
)
@click.option(
    "--exclusions-file",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    default=REFERENCE_PATH,
    show_default=True,
    help="Industry exclusions reference CSV.",
)
def main(
    data_dir: Path,
    run_date: datetime,
    snapshot_date: datetime | None,
    exclusions_file: Path,
) -> None:
    """Build curated universe and exclusion artifacts for one run date."""
    decision_date = run_date.date()
    snapshot = snapshot_date.date() if snapshot_date is not None else decision_date
    result = build_universe(
        data_dir,
        run_date=decision_date,
        snapshot_date=snapshot,
        exclusions_path=exclusions_file,
    )
    click.echo(
        f"Built universe for {decision_date}: "
        f"{result.universe_rows} included, {result.exclusion_rows} excluded."
    )


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
