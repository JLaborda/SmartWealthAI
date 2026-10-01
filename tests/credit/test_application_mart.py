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
            "--bad-value",
            "1",
            "--good-value",
            "0",
            "--decision-date-column",
            "S_2",
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
    assert "bad=1" in result.stdout
    assert "good=0" in result.stdout


def test_build_application_mart_loads_pickle_suffix_alias(tmp_path: Path) -> None:
    """`.pickle` suffix is accepted the same way as `.pkl`."""
    from credit.application_mart import build_application_mart

    alias = tmp_path / "amex_sample.pickle"
    alias.write_bytes(SOURCE_PKL.read_bytes())
    result = build_application_mart(
        alias,
        tmp_path / "out",
        application_id_column="customer_ID",
        target_column="target",
    )
    assert result.retained_rows >= 1
    assert result.mart_path.exists()


def test_build_application_mart_rejects_unsupported_source_format(tmp_path: Path) -> None:
    """Non CSV/pickle sources raise a clear ValueError."""
    from credit.application_mart import build_application_mart

    source = tmp_path / "applications.json"
    source.write_text("[]", encoding="utf-8")
    try:
        build_application_mart(source, tmp_path / "out")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Unsupported source format" in str(exc)


def test_build_application_mart_requires_application_id_presence(tmp_path: Path) -> None:
    """Missing application id column/index name is an explicit error."""
    from credit.application_mart import build_application_mart

    source = tmp_path / "no_id.csv"
    source.write_text("TARGET,AMT_INCOME_TOTAL\n0,100.0\n", encoding="utf-8")
    try:
        build_application_mart(source, tmp_path / "out")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "SK_ID_CURR" in str(exc)


def test_build_application_mart_requires_target_column(tmp_path: Path) -> None:
    """Missing target column is an explicit error."""
    from credit.application_mart import build_application_mart

    source = tmp_path / "no_target.csv"
    source.write_text("SK_ID_CURR,AMT_INCOME_TOTAL\n1,100.0\n", encoding="utf-8")
    try:
        build_application_mart(source, tmp_path / "out")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "TARGET" in str(exc)


def test_build_application_mart_coerces_float16_and_category_for_parquet(
    tmp_path: Path,
) -> None:
    """AMEX-like float16 / category dtypes are normalized before parquet write."""
    from credit.application_mart import build_application_mart

    frame = pd.DataFrame(
        {
            "target": [0, 1],
            "P_2_mean": pd.Series([0.1, 0.9], dtype="float16"),
            "D_63_last": pd.Categorical(["CL", "CO"]),
        },
        index=pd.Index(["cust_x", "cust_y"], name="customer_ID"),
    )
    source = tmp_path / "amex_dtypes.pkl"
    frame.to_pickle(source)

    result = build_application_mart(
        source,
        tmp_path / "out",
        application_id_column="customer_ID",
        target_column="target",
    )
    mart = pd.read_parquet(result.mart_path)
    assert result.retained_rows == 2
    assert mart["P_2_mean"].dtype != "float16"
    assert str(mart["D_63_last"].dtype) != "category"


def test_build_application_mart_writes_empty_mart_when_all_rows_rejected(
    tmp_path: Path,
) -> None:
    """All-reject sources still write an empty mart parquet and reject file."""
    from credit.application_mart import build_application_mart

    frame = pd.DataFrame(
        {"target": [0, 1], "P_2_mean": [0.1, 0.2]},
        index=pd.Index(["", ""], name="customer_ID"),
    )
    source = tmp_path / "amex_all_reject.pkl"
    frame.to_pickle(source)

    result = build_application_mart(
        source,
        tmp_path / "out",
        application_id_column="customer_ID",
        target_column="target",
    )
    mart = pd.read_parquet(result.mart_path)
    rejects = pd.read_parquet(tmp_path / "out" / "rejects.parquet")
    assert result.retained_rows == 0
    assert result.rejected_rows == 2
    assert len(mart) == 0
    assert set(rejects["reject_reason"]) == {"missing_application_id"}


def test_build_application_mart_keeps_non_integral_numeric_ids(tmp_path: Path) -> None:
    """Non-integral numeric application ids are retained without int coercion."""
    from credit.application_mart import build_application_mart

    source = tmp_path / "float_ids.csv"
    source.write_text(
        "SK_ID_CURR,TARGET\n1.5,0\n2.5,1\n",
        encoding="utf-8",
    )
    result = build_application_mart(source, tmp_path / "out")
    mart = pd.read_parquet(result.mart_path)
    assert result.retained_rows == 2
    assert set(mart["SK_ID_CURR"]) == {1.5, 2.5}


def test_cli_parses_non_numeric_and_float_label_values(tmp_path: Path) -> None:
    """CLI label parser accepts string tokens and non-integral floats."""
    source = tmp_path / "labels.csv"
    source.write_text(
        "SK_ID_CURR,TARGET\n1,0\n2,1\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "mart_out"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "credit",
            "build-application-mart",
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
            "--bad-value",
            "default",
            "--good-value",
            "1.5",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "bad=default" in result.stdout
    assert "good=1.5" in result.stdout
    # Numeric 0/1 targets do not match these label tokens → all rejected
    mart = pd.read_parquet(output_dir / "application_mart.parquet")
    assert len(mart) == 0


def test_build_application_mart_preserves_non_numeric_object_ids(tmp_path: Path) -> None:
    """Non-numeric object application ids are kept when float coercion fails."""
    from credit.application_mart import build_application_mart

    frame = pd.DataFrame(
        {"target": [0, 1]},
        index=pd.Index([b"cust_a", b"cust_b"], name="customer_ID"),
    )
    source = tmp_path / "bytes_ids.pkl"
    frame.to_pickle(source)

    result = build_application_mart(
        source,
        tmp_path / "out",
        application_id_column="customer_ID",
        target_column="target",
    )
    mart = pd.read_parquet(result.mart_path)
    assert result.retained_rows == 2
    assert mart["customer_ID"].is_unique
