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
    assert "D_63_mode" in mart.columns
    assert "D_63_last" in mart.columns
    assert "D_64_mode" in mart.columns
    assert "D_64_last" in mart.columns
    assert "B_30_mode" in mart.columns
    assert "B_30_last" in mart.columns
    assert "B_30_mean" not in mart.columns
    assert "D_63_mean" not in mart.columns


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
    assert "mode" in text.lower()
    assert "categorical" in text.lower() or "categoricals" in text.lower()
    assert "statement" in text.lower() or "aggregat" in text.lower()
    assert "D_63" in text
    assert "static competition" in text.lower() or "not point-in-time" in text.lower()
    """CLI build-competition-mart wraps the public competition mart seam."""
    from click.testing import CliRunner

    from credit.cli import main

    raw_dir = _stage_amex_raw(tmp_path / "raw")
    out = tmp_path / "mart"
    result = CliRunner().invoke(
        main,
        [
            "build-competition-mart",
            "--source-kind",
            "amex",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "application_mart.parquet").exists()
    assert "retained" in result.output.lower()


def test_build_competition_mart_cli_home_credit(tmp_path: Path) -> None:
    """CLI build-competition-mart accepts home_credit source kind."""
    from click.testing import CliRunner

    from credit.cli import main

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "application_train.csv").write_text(
        HC_APPLICATION_CSV.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    out = tmp_path / "mart"
    result = CliRunner().invoke(
        main,
        [
            "build-competition-mart",
            "--source-kind",
            "home_credit",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "application_mart.parquet").exists()


def test_build_competition_mart_rejects_unknown_source_kind(tmp_path: Path) -> None:
    """Unknown source_kind fails with a clear error (no silent fallback)."""
    import pytest

    from credit.competition_mart import build_competition_mart

    with pytest.raises(ValueError, match="Unsupported source_kind"):
        build_competition_mart(
            source_kind="fico",  # type: ignore[arg-type]
            raw_dir=tmp_path,
            output_dir=tmp_path / "mart",
        )


def test_prepare_amex_requires_statements_labels_and_key_columns(tmp_path: Path) -> None:
    """AMEX prepare fails when raw files or required columns are missing."""
    import pytest

    from credit.competition_mart import prepare_amex_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    out = tmp_path / "out.parquet"

    with pytest.raises(FileNotFoundError, match="statements"):
        prepare_amex_application_table(raw, out)

    pd.DataFrame({"customer_ID": ["a"], "S_2": ["2017-03-01"], "P_2": [0.1]}).to_parquet(
        raw / "train_data.parquet", index=False
    )
    with pytest.raises(FileNotFoundError, match="labels"):
        prepare_amex_application_table(raw, out)

    (raw / "train_labels.csv").write_text("customer_ID,target\na,0\n", encoding="utf-8")
    pd.DataFrame({"S_2": ["2017-03-01"], "P_2": [0.1]}).to_parquet(
        raw / "train_data.parquet", index=False
    )
    with pytest.raises(ValueError, match="customer_ID"):
        prepare_amex_application_table(raw, out)

    pd.DataFrame({"customer_ID": ["a"], "P_2": [0.1]}).to_parquet(
        raw / "train_data.parquet", index=False
    )
    with pytest.raises(ValueError, match="S_2"):
        prepare_amex_application_table(raw, out)

    pd.DataFrame({"customer_ID": ["a"], "S_2": ["2017-03-01"], "P_2": [0.1]}).to_parquet(
        raw / "train_data.parquet", index=False
    )
    (raw / "train_labels.csv").write_text("id,label\na,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="customer_ID and target"):
        prepare_amex_application_table(raw, out)


def test_prepare_amex_keeps_string_categorical_as_mode_and_last(tmp_path: Path) -> None:
    """String AMEX categoricals (e.g. D_63) survive as mode + last, not dropped."""
    from credit.competition_mart import prepare_amex_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame(
        {
            "customer_ID": ["a", "a", "a", "b"],
            "S_2": ["2017-03-01", "2017-04-01", "2017-05-01", "2017-03-01"],
            "D_63": ["CR", "CO", "CR", "CL"],
            "P_2": [0.1, 0.2, 0.3, 0.4],
        }
    ).to_parquet(raw / "train_data.parquet", index=False)
    (raw / "train_labels.csv").write_text(
        "customer_ID,target\na,0\nb,1\n",
        encoding="utf-8",
    )
    out = tmp_path / "prepared.parquet"
    prepare_amex_application_table(raw, out)
    table = pd.read_parquet(out).set_index("customer_ID")

    assert "D_63_mode" in table.columns
    assert "D_63_last" in table.columns
    assert "D_63_mean" not in table.columns
    assert table.loc["a", "D_63_mode"] == "CR"
    assert table.loc["a", "D_63_last"] == "CR"
    assert table.loc["b", "D_63_mode"] == "CL"
    assert table.loc["b", "D_63_last"] == "CL"
    assert "P_2_mean" in table.columns
    assert "P_2_last" in table.columns


def test_prepare_amex_aggregates_numeric_categoricals_with_mode_and_last(
    tmp_path: Path,
) -> None:
    """Official numeric-coded AMEX categoricals get mode + last only (no mean/std)."""
    from credit.competition_mart import prepare_amex_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame(
        {
            "customer_ID": ["a", "a", "a"],
            "S_2": ["2017-03-01", "2017-04-01", "2017-05-01"],
            "B_30": [0, 1, 0],
            "D_68": [2.0, 3.0, 2.0],
            "P_2": [0.1, 0.2, 0.3],
        }
    ).to_parquet(raw / "train_data.parquet", index=False)
    (raw / "train_labels.csv").write_text(
        "customer_ID,target\na,0\n",
        encoding="utf-8",
    )
    out = tmp_path / "prepared.parquet"
    prepare_amex_application_table(raw, out)
    table = pd.read_parquet(out)

    assert "B_30_mode" in table.columns
    assert "B_30_last" in table.columns
    assert "B_30_mean" not in table.columns
    assert "B_30_std" not in table.columns
    assert "D_68_mode" in table.columns
    assert "D_68_last" in table.columns
    assert "D_68_mean" not in table.columns
    assert table.loc[0, "B_30_mode"] == 0
    assert table.loc[0, "B_30_last"] == 0
    assert table.loc[0, "D_68_mode"] == 2.0
    assert table.loc[0, "D_68_last"] == 2.0
    assert "P_2_mean" in table.columns
    assert "P_2_last" in table.columns


def test_prepare_amex_allows_non_numeric_only_statements(tmp_path: Path) -> None:
    """AMEX prepare keeps non-numeric features (mode + last); no silent string drops."""
    from credit.competition_mart import prepare_amex_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame(
        {
            "customer_ID": ["a", "a", "b"],
            "S_2": ["2017-03-01", "2017-04-01", "2017-03-01"],
            "note": ["x", "y", "z"],
        }
    ).to_parquet(raw / "train_data.parquet", index=False)
    (raw / "train_labels.csv").write_text(
        "customer_ID,target\na,0\nb,1\n",
        encoding="utf-8",
    )
    out = tmp_path / "prepared.parquet"
    prepare_amex_application_table(raw, out)
    table = pd.read_parquet(out).set_index("customer_ID")
    assert set(table.index) == {"a", "b"}
    assert set(table["target"]) == {0, 1}
    assert "note_mode" in table.columns
    assert "note_last" in table.columns
    assert table.loc["a", "note_mode"] in {"x", "y"}
    assert table.loc["a", "note_last"] == "y"
    assert table.loc["b", "note_last"] == "z"


def test_prepare_amex_id_and_date_only_still_emits_labeled_rows(tmp_path: Path) -> None:
    """AMEX prepare emits customer rows when statements have no feature columns."""
    from credit.competition_mart import prepare_amex_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame(
        {
            "customer_ID": ["a", "a", "b"],
            "S_2": ["2017-03-01", "2017-04-01", "2017-03-01"],
        }
    ).to_parquet(raw / "train_data.parquet", index=False)
    (raw / "train_labels.csv").write_text(
        "customer_ID,target\na,0\nb,1\n",
        encoding="utf-8",
    )
    out = tmp_path / "prepared.parquet"
    prepare_amex_application_table(raw, out)
    table = pd.read_parquet(out)
    assert set(table["customer_ID"]) == {"a", "b"}
    assert set(table["target"]) == {0, 1}


def test_prepare_amex_all_null_categorical_mode_is_null(tmp_path: Path) -> None:
    """All-null categorical history yields a null mode (not a crash)."""
    from credit.competition_mart import prepare_amex_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame(
        {
            "customer_ID": ["a", "a"],
            "S_2": ["2017-03-01", "2017-04-01"],
            "D_63": [pd.NA, pd.NA],
            "P_2": [0.1, 0.2],
        }
    ).to_parquet(raw / "train_data.parquet", index=False)
    (raw / "train_labels.csv").write_text(
        "customer_ID,target\na,0\n",
        encoding="utf-8",
    )
    out = tmp_path / "prepared.parquet"
    prepare_amex_application_table(raw, out)
    table = pd.read_parquet(out)
    assert "D_63_mode" in table.columns
    assert pd.isna(table.loc[0, "D_63_mode"])
    assert pd.isna(table.loc[0, "D_63_last"])


def test_prepare_home_credit_requires_application_train_shape(tmp_path: Path) -> None:
    """Home Credit prepare fails without application_train or required columns."""
    import pytest

    from credit.competition_mart import prepare_home_credit_application_table

    raw = tmp_path / "raw"
    raw.mkdir()
    out = tmp_path / "out.parquet"

    with pytest.raises(FileNotFoundError, match="application"):
        prepare_home_credit_application_table(raw, out)

    (raw / "application_train.csv").write_text("FOO,BAR\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SK_ID_CURR and TARGET"):
        prepare_home_credit_application_table(raw, out)


def test_home_credit_mart_readme_documents_pass_through_contract(tmp_path: Path) -> None:
    """Home Credit mart README documents the pass-through prepare contract."""
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
    text = result.readme_path.read_text(encoding="utf-8")
    assert "home credit" in text.lower()
    assert "pass-through" in text.lower() or "application_train" in text.lower()


def test_build_application_mart_accepts_parquet_source(tmp_path: Path) -> None:
    """Existing mart seam loads application-grain parquet sources."""
    from credit.application_mart import build_application_mart

    source = tmp_path / "apps.parquet"
    pd.read_csv(FIXTURES / "application_source" / "applications.csv").to_parquet(
        source, index=False
    )
    result = build_application_mart(source, tmp_path / "mart")
    assert result.retained_rows >= 1
    assert result.mart_path.exists()
