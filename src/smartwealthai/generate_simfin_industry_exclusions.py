"""Regenerate ``data/reference/simfin_industry_exclusions.csv`` from SimFin industries."""

from __future__ import annotations

from pathlib import Path

import click
import pandas as pd
from click.testing import CliRunner

from smartwealthai.simfin_industry_exclusions import (
    REFERENCE_PATH,
    build_exclusions,
    write_exclusions,
)


def run_generate(*, industries_path: Path, output_path: Path) -> Path:
    """Build and write the exclusions CSV from a SimFin industries bulk file."""
    industries = pd.read_csv(industries_path, sep=";", index_col="IndustryId")
    exclusions = build_exclusions(industries)
    return write_exclusions(exclusions, output_path)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--industries",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    required=True,
    help="SimFin industries bulk CSV (semicolon-separated).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    default=REFERENCE_PATH,
    show_default=True,
    help="Destination exclusions CSV.",
)
def main(industries: Path, output: Path) -> None:
    """Regenerate the versioned SimFin industry exclusions reference CSV."""
    path = run_generate(industries_path=industries, output_path=output)
    click.echo(f"Wrote {len(pd.read_csv(path))} rows to {path}")


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
