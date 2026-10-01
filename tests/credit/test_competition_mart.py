"""Public-interface tests for competition → application mart (#152)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from credit.amex_parquet import convert_amex_extract_to_parquet

FIXTURES = Path(__file__).resolve().parent / "fixtures"
AMEX_STATEMENTS_CSV = FIXTURES / "amex_extract" / "train_data_tiny.csv"
AMEX_LABELS_CSV = FIXTURES / "competition_mart" / "amex" / "train_labels.csv"
HC_APPLICATION_CSV = FIXTURES / "competition_mart" / "home_credit" / "application_train.csv"


def _stage_amex_raw(raw_dir: Path) -> Path:
    """Hermetic AMEX raw layout: statement parquet + labels CSV."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    convert_amex_extract_to_parquet(
        AMEX_STATEMENTS_CSV,
        raw_dir / "train_data.parquet",
    )
    (raw_dir / "train_labels.csv").write_text(
        AMEX_LABELS_CSV.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return raw_dir


def test_build_competition_mart_amex_one_row_per_customer_with_target(
    tmp_path: Path,
) -> None:
    """AMEX statements aggregate to one customer row with joined target."""
    from credit.competition_mart import build_competition_mart

    raw_dir = _stage_amex_raw(tmp_path / "raw")
    result = build_competition_mart(
        source_kind="amex",
        raw_dir=raw_dir,
        output_dir=tmp_path / "mart",
    )

    mart = pd.read_parquet(result.mart_path)
    assert result.retained_rows == 2
    assert result.rejected_rows == 0
    assert result.target_column == "target"
    assert result.bad_value == 1
    assert result.good_value == 0
    assert mart["customer_ID"].is_unique
    assert set(mart["target"]) <= {0, 1}
    assert "P_2_mean" in mart.columns
    assert "P_2_last" in mart.columns


def test_build_competition_mart_home_credit_application_grain(tmp_path: Path) -> None:
    """Home Credit application_train becomes a validated application mart."""
    from credit.competition_mart import build_competition_mart

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "application_train.csv").write_text(
        HC_APPLICATION_CSV.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = build_competition_mart(
        source_kind="home_credit",
        raw_dir=raw_dir,
        output_dir=tmp_path / "mart",
    )

    mart = pd.read_parquet(result.mart_path)
    assert result.retained_rows == 3
    assert result.rejected_rows == 0
    assert result.target_column == "TARGET"
    assert result.bad_value == 1
    assert result.good_value == 0
    assert mart["SK_ID_CURR"].is_unique
    assert set(mart["TARGET"]) <= {0, 1}


def test_competition_mart_readme_documents_target_and_source_contract(
    tmp_path: Path,
) -> None:
    """Mart README documents bad/good and the competition prepare contract."""
    from credit.competition_mart import build_competition_mart

    raw_dir = _stage_amex_raw(tmp_path / "raw")
    result = build_competition_mart(
        source_kind="amex",
        raw_dir=raw_dir,
        output_dir=tmp_path / "mart",
    )
    text = result.readme_path.read_text(encoding="utf-8")

    assert "target" in text.lower()
    assert "bad" in text.lower()
    assert "good" in text.lower()
    assert "amex" in text.lower()
    assert "mean" in text.lower() and "last" in text.lower()
    assert "statement" in text.lower() or "aggregat" in text.lower()


def test_build_competition_mart_cli_amex(tmp_path: Path) -> None:
    """CLI build-competition-mart wraps the public competition mart seam."""
    import subprocess
    import sys

    raw_dir = _stage_amex_raw(tmp_path / "raw")
    out = tmp_path / "mart"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "credit",
            "build-competition-mart",
            "--source-kind",
            "amex",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "application_mart.parquet").exists()
    assert "retained" in proc.stdout.lower()
