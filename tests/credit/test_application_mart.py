"""Public-interface tests for application mart build (#144)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "application_source"
SOURCE_CSV = FIXTURES / "applications.csv"
SOURCE_PKL = FIXTURES / "amex_sample.pkl"


def test_build_application_mart_writes_mart_from_fixture(tmp_path: Path) -> None:
    """build_application_mart writes an application mart artifact from a local fixture."""
    from credit.application_mart import build_application_mart

    result = build_application_mart(SOURCE_CSV, tmp_path)

    assert result.mart_path.exists()
    assert result.retained_rows >= 1


def test_application_mart_has_one_row_per_application_and_binary_target(
    tmp_path: Path,
) -> None:
    """Mart grain is one application id per row with a binary target present."""
    from credit.application_mart import build_application_mart

    result = build_application_mart(SOURCE_CSV, tmp_path)
    mart = pd.read_parquet(result.mart_path)

    assert result.target_column in mart.columns
    assert mart["SK_ID_CURR"].is_unique
    assert set(mart[result.target_column].unique()) <= {result.bad_value, result.good_value}
    assert result.bad_value == 1
    assert result.good_value == 0


def test_application_mart_sidecar_documents_target_bad_and_good(tmp_path: Path) -> None:
    """README sidecar documents which target value means bad (and good)."""
    from credit.application_mart import build_application_mart

    result = build_application_mart(SOURCE_CSV, tmp_path)
    text = result.readme_path.read_text(encoding="utf-8")

    assert result.readme_path.exists()
    assert "TARGET" in text
    assert "bad" in text.lower()
    assert "good" in text.lower()
    assert "`1`" in text or "1" in text
    assert "not live bank" in text.lower() or "public demo" in text.lower()


def test_application_mart_rejects_unusable_rows_without_silence(tmp_path: Path) -> None:
    """Unusable rows increment rejected_rows and are excluded from the mart."""
    from credit.application_mart import build_application_mart

    result = build_application_mart(SOURCE_CSV, tmp_path)
    mart = pd.read_parquet(result.mart_path)

    assert result.rejected_rows >= 1
    assert result.retained_rows == len(mart)
    assert result.retained_rows + result.rejected_rows == len(pd.read_csv(SOURCE_CSV))
    rejects = pd.read_parquet(tmp_path / "rejects.parquet")
    assert len(rejects) == result.rejected_rows
    assert "reject_reason" in rejects.columns
    # Fixture includes null target, null id, invalid target, and a duplicate id
    assert 100004 not in set(mart["SK_ID_CURR"])
    assert 100005 not in set(mart["SK_ID_CURR"])


def test_application_mart_documents_stratified_random_split_policy(
    tmp_path: Path,
) -> None:
    """Without a decision date column, sidecar documents stratified random policy."""
    from credit.application_mart import build_application_mart

    result = build_application_mart(SOURCE_CSV, tmp_path)
    text = result.readme_path.read_text(encoding="utf-8")

    assert result.split_policy == "stratified_random"
    assert "stratified random" in text.lower()
    assert "develop" in text.lower() and "holdout" in text.lower()


def test_application_mart_documents_time_based_split_policy_when_date_present(
    tmp_path: Path,
) -> None:
    """With a decision date column on the source, sidecar documents time-based policy."""
    from credit.application_mart import build_application_mart

    source = tmp_path / "with_date.csv"
    source.write_text(
        "SK_ID_CURR,TARGET,AMT_INCOME_TOTAL,DECISION_DATE\n"
        "200001,0,100000.0,2024-01-15\n"
        "200002,1,150000.0,2024-02-01\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = build_application_mart(
        source,
        out,
        decision_date_column="DECISION_DATE",
    )
    text = result.readme_path.read_text(encoding="utf-8")

    assert result.split_policy == "time_based"
    assert "time-based" in text.lower()
    assert "DECISION_DATE" in text


def test_cli_build_application_mart_writes_mart_from_fixture(tmp_path: Path) -> None:
    """CLI stage build-application-mart invokes the seam on fixture data."""
    output_dir = tmp_path / "mart_out"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "credit",
            "build-application-mart",
            "--source",
            str(SOURCE_CSV),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert (output_dir / "application_mart.parquet").exists()
    assert (output_dir / "README.md").exists()
    assert "retained" in result.stdout.lower()
    assert "rejected" in result.stdout.lower()


def test_build_application_mart_loads_amex_shaped_pickle(tmp_path: Path) -> None:
    """Pickle sources with customer_ID index and lowercase target are supported."""
    from credit.application_mart import build_application_mart

    result = build_application_mart(
        SOURCE_PKL,
        tmp_path,
        application_id_column="customer_ID",
        target_column="target",
        bad_value=1,
        good_value=0,
    )
    mart = pd.read_parquet(result.mart_path)

    assert result.retained_rows >= 1
    assert result.rejected_rows >= 1
    assert "customer_ID" in mart.columns
    assert mart["customer_ID"].is_unique
    assert set(mart["target"].unique()) <= {0, 1}
    text = result.readme_path.read_text(encoding="utf-8")
    assert "target" in text
    assert "`1`" in text or "1" in text


def test_cli_build_application_mart_accepts_pickle_column_overrides(
    tmp_path: Path,
) -> None:
    """CLI passes AMEX-shaped id/target column overrides through to the seam."""
    output_dir = tmp_path / "mart_out"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "credit",
            "build-application-mart",
            "--source",
            str(SOURCE_PKL),
            "--output-dir",
            str(output_dir),
            "--application-id-column",
            "customer_ID",
            "--target-column",
            "target",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    mart = pd.read_parquet(output_dir / "application_mart.parquet")
    assert "customer_ID" in mart.columns
    assert "target" in mart.columns
