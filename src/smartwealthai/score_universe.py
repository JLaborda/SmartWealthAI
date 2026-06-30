"""CLI to score the demo universe and build the Magic Formula ranking + portfolio."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.cli_lake import lake_root_options, resolve_cli_data_dir
from smartwealthai.magic_formula_ranking import score_universe
from smartwealthai.normalize_simfin import resolve_show_progress


def format_scoring_summary(result: object) -> str:
    """Render a human-readable scoring run summary."""
    from smartwealthai.magic_formula_ranking import ScoringResult

    if not isinstance(result, ScoringResult):
        msg = "expected ScoringResult"
        raise TypeError(msg)
    lines = [
        f"Scoring run for {result.run_date}",
        f"  Rankable tickers: {result.rankable_count}",
        f"  Portfolio holdings: {result.portfolio_count}",
    ]
    if result.mlflow_run_id:
        lines.append(f"  MLflow run id: {result.mlflow_run_id}")
    lines.extend(
        [
            "",
            "Artifacts:",
            f"  quality:  {result.quality_path}",
            f"  cheap:    {result.cheap_path}",
            f"  combined: {result.combined_path}",
            f"  portfolio:{result.portfolio_path}",
        ]
    )
    return "\n".join(lines)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@lake_root_options
@click.option(
    "--run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: datetime.now(tz=UTC).strftime("%Y-%m-%d"),
    show_default="today (UTC)",
    help="Decision date for universe, prices, and PIT fundamentals.",
)
@click.option(
    "--portfolio-size",
    type=int,
    default=30,
    show_default=True,
    help="Number of equal-weight holdings (or fewer when universe is smaller).",
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
    lake_root_uri: str | None,
    data_dir: Path | None,
    run_date: datetime,
    portfolio_size: int,
    progress: bool,
    quiet: bool,
) -> None:
    """Score the demo universe and write ranking + portfolio parquets."""
    try:
        lake_path = resolve_cli_data_dir(lake_root_uri=lake_root_uri, data_dir=data_dir)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    decision_date = run_date.date()
    try:
        result = score_universe(
            lake_path,
            run_date=decision_date,
            portfolio_size=portfolio_size,
            show_progress=resolve_show_progress(progress=progress, quiet=quiet),
        )
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc

    click.echo(format_scoring_summary(result))


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [], catch_exceptions=False)
    return result.exit_code


if __name__ == "__main__":
    main()
