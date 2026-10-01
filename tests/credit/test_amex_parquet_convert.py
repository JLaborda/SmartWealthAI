"""Public-interface tests for AMEX extract → parquet conversion (#151)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "amex_extract"
SOURCE_CSV = FIXTURES / "train_data_tiny.csv"


def test_convert_amex_extract_writes_parquet_with_same_rows_and_customer_ids(
    tmp_path: Path,
) -> None:
    """Official-shaped AMEX CSV converts to parquet with identical row identity."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    source = pd.read_csv(SOURCE_CSV)
    out = tmp_path / "train_data.parquet"

    result = convert_amex_extract_to_parquet(SOURCE_CSV, out)

    assert result.parquet_path == out
    assert result.parquet_path.exists()
    assert result.row_count == len(source)
    got = pd.read_parquet(result.parquet_path)
    assert list(got.columns) == list(source.columns)
    assert got["customer_ID"].tolist() == source["customer_ID"].tolist()
    # Missing values stay missing (no community-style int8 NA sentinels).
    assert pd.isna(got.loc[2, "P_2"])
    assert pd.isna(got.loc[1, "B_1"])


def test_convert_amex_extract_downcasts_float64_to_float32(tmp_path: Path) -> None:
    """Optional float64→float32 downcast is the only dtype change by default."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    out = tmp_path / "train_data.parquet"
    convert_amex_extract_to_parquet(SOURCE_CSV, out)
    got = pd.read_parquet(out)

    assert str(got["P_2"].dtype) == "float32"
    assert str(got["D_39"].dtype) == "float32"
    assert str(got["B_1"].dtype) == "float32"
    assert not pd.api.types.is_float_dtype(got["customer_ID"])
