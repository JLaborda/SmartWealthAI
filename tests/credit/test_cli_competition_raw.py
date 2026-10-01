"""Public-interface tests for competition-raw CLI commands (#151)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from click.testing import CliRunner

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "amex_extract"
SOURCE_CSV = FIXTURES / "train_data_tiny.csv"


def test_cli_convert_amex_extract_writes_parquet(tmp_path: Path) -> None:
    """credit-css convert-amex-extract writes parquet from a local CSV."""
    from credit.cli import main

    out = tmp_path / "train_data.parquet"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convert-amex-extract",
            "--source",
            str(SOURCE_CSV),
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "row" in result.output.lower() or "parquet" in result.output.lower()


def test_cli_stage_competition_extract_unzips(tmp_path: Path) -> None:
    """credit-css stage-competition-extract unpacks a zip into dest."""
    from credit.cli import main

    zip_path = tmp_path / "extract.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("application_train.csv", "SK_ID_CURR,TARGET\n1,0\n")
    dest = tmp_path / "raw" / "home_credit"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "stage-competition-extract",
            "--source",
            str(zip_path),
            "--dest-dir",
            str(dest),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (dest / "application_train.csv").is_file()
