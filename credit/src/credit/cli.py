"""Credit Scoring System (CSS) CLI — composable stages (#143 stub; #144 mart)."""

from __future__ import annotations

from pathlib import Path

import click

from credit import __version__
from credit.application_mart import build_application_mart


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
    help=(
        "Credit Scoring System (CSS) CLI. "
        "Application credit scoring stages: build-application-mart "
        "(scratch scoring lands in a later ticket)."
    ),
)
@click.version_option(__version__, prog_name="credit-css")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Entry point for the ``credit-css`` console script."""
    if ctx.invoked_subcommand is None:
        click.echo(
            "Credit Scoring System (CSS) CLI.\n"
            "Stages: build-application-mart\n"
            "See credit/docs/features/css-chapter5-mart-and-scoring.md."
        )


@main.command("build-application-mart")
@click.option(
    "--source",
    "source_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    required=True,
    help="Local application source table (CSV).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Directory for the application mart artifact and README sidecar.",
)
def build_application_mart_cmd(source_path: Path, output_dir: Path) -> None:
    """Build a validated application mart from local demo source data."""
    result = build_application_mart(source_path, output_dir)
    click.echo(
        f"Application mart written: {result.mart_path} "
        f"({result.retained_rows} retained, {result.rejected_rows} rejected). "
        f"Target `{result.target_column}`: bad={result.bad_value}, "
        f"good={result.good_value}. Split policy: {result.split_policy}. "
        f"Sidecar: {result.readme_path}"
    )
