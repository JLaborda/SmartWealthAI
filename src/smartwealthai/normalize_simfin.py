"""CLI to normalize SimFin bulk CSVs into curated fundamentals parquet."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import click
import pandas as pd
from click.testing import CliRunner

from smartwealthai.lake_paths import curated_universe_path
from smartwealthai.simfin_normalizer import DEFAULT_MAPPING_PATH, normalize_simfin


def resolve_show_progress(*, progress: bool, quiet: bool) -> bool | None:
    """Map CLI flags to normalize_simfin show_progress (None = auto-detect TTY)."""
    if progress and quiet:
        msg = "Pass only one of --progress or --quiet."
        raise click.ClickException(msg)
    if quiet:
        return False
    if progress:
        return True
    return None


def load_universe_tickers(data_dir: Path, run_date: date) -> set[str]:
    """Load investable tickers from a curated universe snapshot."""
    path = curated_universe_path(data_dir, run_date=run_date)
    if not path.exists():
        msg = (
            f"Universe not found: {path}. "
            "Run build-universe first or pass --ticker for smoke tests."
        )
        raise click.ClickException(msg)
    universe = pd.read_parquet(path)
    return {str(ticker).upper() for ticker in universe["ticker"]}


def resolve_normalize_tickers(
    data_dir: Path,
    *,
    universe_run_date: date | None,
    explicit_tickers: tuple[str, ...],
) -> set[str]:
    """Merge universe and explicit ticker filters into the normalizer scope."""
    ticker_set: set[str] | None = None
    if universe_run_date is not None:
        ticker_set = load_universe_tickers(data_dir, universe_run_date)
    if explicit_tickers:
        explicit = {ticker.upper() for ticker in explicit_tickers}
        ticker_set = explicit if ticker_set is None else ticker_set & explicit
    if ticker_set is None:
        msg = (
            "Pass --universe-run-date (after build-universe) or --ticker to limit scope. "
            "See docs/mvp/guides/download-simfin.md."
        )
        raise click.ClickException(msg)
    return ticker_set


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
    "--universe-run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Load tickers from curated/universe for this run date (requires build-universe).",
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
@click.option(
    "--progress",
    is_flag=True,
    help="Show progress bars even when stderr is not a TTY.",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress progress bars.",
)
def main(
    data_dir: Path,
    snapshot_date: datetime,
    universe_run_date: datetime | None,
    mapping: Path,
    tickers: tuple[str, ...],
    progress: bool,
    quiet: bool,
) -> None:
    """Normalize raw SimFin bulk snapshots into curated PIT fundamentals."""
    snapshot = snapshot_date.date()
    universe_date = universe_run_date.date() if universe_run_date is not None else None
    ticker_set = resolve_normalize_tickers(
        data_dir,
        universe_run_date=universe_date,
        explicit_tickers=tickers,
    )
    result = normalize_simfin(
        data_dir,
        snapshot_date=snapshot,
        mapping_path=mapping,
        tickers=ticker_set,
        run_date=universe_date or snapshot,
        show_progress=resolve_show_progress(progress=progress, quiet=quiet),
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
