"""Launch the demo Streamlit dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Lake root (sets SMARTWEALTHAI_DATA_DIR).",
)
@click.option(
    "--run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Pipeline run date to display (sets SMARTWEALTHAI_RUN_DATE).",
)
def main(data_dir: Path | None, run_date: click.DateTime | None) -> None:
    """Run the three-page demo dashboard (Overview, Ranking, Portfolio)."""
    env = os.environ.copy()
    if data_dir is not None:
        env["SMARTWEALTHAI_DATA_DIR"] = str(data_dir)
    if run_date is not None:
        env["SMARTWEALTHAI_RUN_DATE"] = run_date.strftime("%Y-%m-%d")

    root = _repo_root()
    pythonpath = str(root)
    if existing := env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{existing}"
    env["PYTHONPATH"] = pythonpath

    home = root / "apps" / "dashboard" / "Home.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(home)],
        check=True,
        env=env,
    )


if __name__ == "__main__":
    main()
