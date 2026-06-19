"""CLI to normalize SimFin bulk CSVs into curated fundamentals parquet."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.simfin_normalizer import DEFAULT_MAPPING_PATH, normalize_simfin


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data"),
    show_default=True,
    help="Data lake root.",
)
@click.option(
    "--snapshot-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: datetime.now(tz=UTC).strftime("%Y-%m-%d"),
    show_default="today (UTC)",
    help="Raw SimFin bulk partition date to normalize.",
)
@click.option(
    "--mapping",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    default=DEFAULT_MAPPING_PATH,
    show_default=True,
    help="SimFin column mapping YAML.",
)
@click.option(
    "--ticker",
    "tickers",
    multiple=True,
    help="Limit normalization to one or more tickers (repeatable).",
)
def main(
    data_dir: Path,
    snapshot_date: datetime,
    mapping: Path,
    tickers: tuple[str, ...],
) -> None:
    """Normalize raw SimFin bulk snapshots into curated PIT fundamentals."""
    snapshot = snapshot_date.date()
    ticker_set = set(tickers) if tickers else None
    result = normalize_simfin(
        data_dir,
        snapshot_date=snapshot,
        mapping_path=mapping,
        tickers=ticker_set,
        run_date=snapshot,
    )
    click.echo(
        f"Normalized snapshot {snapshot}: "
        f"{result.written_rows} curated row(s), {result.issue_rows} issue row(s)."
    )


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
