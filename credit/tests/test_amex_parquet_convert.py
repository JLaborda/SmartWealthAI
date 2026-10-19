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


def test_convert_amex_extract_keeps_float64_when_downcast_disabled(tmp_path: Path) -> None:
    """downcast_float64=False leaves float columns as float64."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    out = tmp_path / "train_data.parquet"
    convert_amex_extract_to_parquet(SOURCE_CSV, out, downcast_float64=False)
    got = pd.read_parquet(out)

    assert str(got["P_2"].dtype) == "float64"
    assert str(got["D_39"].dtype) == "float64"
    assert str(got["B_1"].dtype) == "float64"


def test_convert_amex_extract_streams_multiple_chunks(tmp_path: Path) -> None:
    """chunksize smaller than the file still writes one parquet with every row."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    source = pd.read_csv(SOURCE_CSV)
    out = tmp_path / "nested" / "train_data.parquet"
    result = convert_amex_extract_to_parquet(SOURCE_CSV, out, chunksize=1)

    assert result.row_count == len(source)
    got = pd.read_parquet(out)
    assert got["customer_ID"].tolist() == source["customer_ID"].tolist()
    assert pd.isna(got.loc[2, "P_2"])


def test_convert_amex_extract_replaces_existing_parquet(tmp_path: Path) -> None:
    """An existing output path is replaced rather than appended."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    out = tmp_path / "train_data.parquet"
    out.write_bytes(b"stale")
    result = convert_amex_extract_to_parquet(SOURCE_CSV, out, chunksize=1)

    assert result.row_count == 3
    assert out.read_bytes()[:4] == b"PAR1"


def test_convert_amex_extract_rejects_missing_source(tmp_path: Path) -> None:
    """A missing CSV is an explicit FileNotFoundError."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    try:
        convert_amex_extract_to_parquet(tmp_path / "missing.csv", tmp_path / "out.parquet")
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError as exc:
        assert "missing.csv" in str(exc)


def test_convert_amex_extract_rejects_chunksize_below_one(tmp_path: Path) -> None:
    """chunksize must be a positive row count."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    try:
        convert_amex_extract_to_parquet(SOURCE_CSV, tmp_path / "out.parquet", chunksize=0)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "chunksize" in str(exc)


def test_convert_amex_extract_requires_customer_id(tmp_path: Path) -> None:
    """Extracts without customer_ID are rejected."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    source = tmp_path / "no_id.csv"
    source.write_text("S_2,P_2\n2017-03-01,0.1\n", encoding="utf-8")
    try:
        convert_amex_extract_to_parquet(source, tmp_path / "out.parquet")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "customer_ID" in str(exc)


def test_convert_amex_extract_rejects_empty_csv(tmp_path: Path) -> None:
    """A header-only CSV is an explicit error and writes no parquet."""
    from credit.amex_parquet import convert_amex_extract_to_parquet

    source = tmp_path / "empty.csv"
    source.write_text("customer_ID,P_2\n", encoding="utf-8")
    out = tmp_path / "out.parquet"
    try:
        convert_amex_extract_to_parquet(source, out)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "empty" in str(exc)
    assert not out.exists()
