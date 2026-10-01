"""Credit Scoring System (CSS) CLI — composable stages (#143 stub; #144 mart; #147 pkl)."""

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
    help="Local application source table (.csv, .pkl, or .pickle).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Directory for the application mart artifact and README sidecar.",
)
@click.option(
    "--application-id-column",
    default="SK_ID_CURR",
    show_default=True,
    help="Application id column (or index name for AMEX-shaped pickles).",
)
@click.option(
    "--target-column",
    default="TARGET",
    show_default=True,
    help="Binary target column name.",
)
@click.option(
    "--bad-value",
    default="1",
    show_default=True,
    help="Target value that means bad (default / positive class).",
)
@click.option(
    "--good-value",
    default="0",
    show_default=True,
    help="Target value that means good (negative class).",
)
@click.option(
    "--decision-date-column",
    default=None,
    help="Optional application/decision date column for time-based split docs.",
)
def build_application_mart_cmd(
    source_path: Path,
    output_dir: Path,
    application_id_column: str,
    target_column: str,
    bad_value: str,
    good_value: str,
    decision_date_column: str | None,
) -> None:
    """Build a validated application mart from local demo source data."""
    result = build_application_mart(
        source_path,
        output_dir,
        application_id_column=application_id_column,
        target_column=target_column,
        bad_value=_parse_label_value(bad_value),
        good_value=_parse_label_value(good_value),
        decision_date_column=decision_date_column,
    )
    click.echo(
        f"Application mart written: {result.mart_path} "
        f"({result.retained_rows} retained, {result.rejected_rows} rejected). "
        f"Target `{result.target_column}`: bad={result.bad_value}, "
        f"good={result.good_value}. Split policy: {result.split_policy}. "
        f"Sidecar: {result.readme_path}"
    )


def _parse_label_value(raw: str) -> object:
    """Parse CLI label tokens; prefer ints when the token is integral."""
    try:
        as_float = float(raw)
    except ValueError:
        return raw
    if as_float == int(as_float):
        return int(as_float)
    return as_float
