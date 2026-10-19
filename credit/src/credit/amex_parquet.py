"""Convert official AMEX competition CSV extracts to local parquet (#151).

Controlled conversion only: preserve row identity and missingness. Optional
float64→float32 downcast for size. No community-style NA→-127 / category int
recoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class AmexParquetResult:
    """Outcome of converting one AMEX CSV extract to parquet."""

    parquet_path: Path
    row_count: int
    source_path: Path


def convert_amex_extract_to_parquet(
    source_csv: Path,
    output_parquet: Path,
    *,
    downcast_float64: bool = True,
    chunksize: int = 500_000,
) -> AmexParquetResult:
    """Write ``source_csv`` to ``output_parquet`` with stable row identity.

    Parameters
    ----------
    source_csv:
        Official (or fixture) AMEX-shaped CSV with a ``customer_ID`` column.
    output_parquet:
        Destination parquet path (parent dirs are created).
    downcast_float64:
        If True, cast float64 columns to float32 after load (size only).
    chunksize:
        Rows per read chunk (keeps peak RAM bounded on multi-GB extracts).
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    source_csv = Path(source_csv)
    output_parquet = Path(output_parquet)
    if not source_csv.is_file():
        raise FileNotFoundError(f"AMEX extract CSV not found: {source_csv}")
    if chunksize < 1:
        raise ValueError("chunksize must be >= 1")

    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    if output_parquet.exists():
        output_parquet.unlink()

    reader = pd.read_csv(source_csv, chunksize=chunksize)
    writer: pq.ParquetWriter | None = None
    row_count = 0

    try:
        for chunk in reader:
            if "customer_ID" not in chunk.columns:
                raise ValueError("AMEX extract must include a customer_ID column")
            if downcast_float64:
                float64_cols = chunk.select_dtypes(include=["float64"]).columns
                for col in float64_cols:
                    chunk[col] = chunk[col].astype("float32")
            table = pa.Table.from_pandas(chunk, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output_parquet, table.schema)
            writer.write_table(table)
            row_count += len(chunk)
    finally:
        # ponytail: pandas yields a chunk or raises first, so writer is None
        # only when this try is already failing. The finished-loop fall-through
        # is unreachable; upgrade path is a reader that can be empty.
        if writer is not None:  # pragma: no branch
            writer.close()

    if row_count == 0:
        # pandas yields one empty chunk for a header-only file, so the writer
        # may already have created a 0-row parquet.
        output_parquet.unlink(missing_ok=True)
        raise ValueError("AMEX extract CSV was empty")

    return AmexParquetResult(
        parquet_path=output_parquet,
        row_count=row_count,
        source_path=source_csv,
    )
