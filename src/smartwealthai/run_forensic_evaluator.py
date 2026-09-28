"""CLI to run the forensic evaluator / permanent-loss filter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.forensic_evaluator import run_forensic_evaluator


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
    help="Decision date for forensic evaluation.",
)
def main(data_dir: Path, run_date: datetime) -> None:
    """Run forensic hard-exclusion rules and write permanent-loss artifacts."""
    decision_date = run_date.date()
    result = run_forensic_evaluator(data_dir, run_date=decision_date)
    click.echo(
        f"Forensic evaluation for {decision_date}: "
        f"{result.evaluated_count} evaluated, "
        f"{result.exclusion_count} excluded, "
        f"{result.review_count} review queue."
    )
    click.echo(f"  Exclusions: {result.exclusions_path}")
    if result.issues_path is not None:
        click.echo(f"  Review queue: {result.issues_path}")


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
