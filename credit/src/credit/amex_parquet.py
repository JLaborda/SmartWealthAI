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
    """
    source_csv = Path(source_csv)
    output_parquet = Path(output_parquet)
    if not source_csv.is_file():
        raise FileNotFoundError(f"AMEX extract CSV not found: {source_csv}")

    frame = pd.read_csv(source_csv)
    if "customer_ID" not in frame.columns:
        raise ValueError("AMEX extract must include a customer_ID column")

    if downcast_float64:
        float64_cols = frame.select_dtypes(include=["float64"]).columns
        for col in float64_cols:
            frame[col] = frame[col].astype("float32")

    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_parquet, index=False)
    return AmexParquetResult(
        parquet_path=output_parquet,
        row_count=len(frame),
        source_path=source_csv,
    )
