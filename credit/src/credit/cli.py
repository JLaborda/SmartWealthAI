"""Credit CSS CLI stub — help and version only (#143; mart is #144)."""

from __future__ import annotations

import click

from credit import __version__


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "Credit Scoring System (CSS) CLI. "
        "Application credit scoring stages land in later tickets "
        "(application mart, then scratch scoring)."
    ),
)
@click.version_option(__version__, prog_name="credit-css")
def main() -> None:
    """Entry point for the ``credit-css`` console script."""
    click.echo(
        "Credit Scoring System (CSS) CLI stub. "
        "No stages yet — see credit/docs/features/css-chapter5-mart-and-scoring.md."
    )
