"""SimFin industry exclusions reference for the demo universe."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REFERENCE_PATH = Path("data/reference/simfin_industry_exclusions.csv")
EXCLUSION_COLUMNS = ("industry_id", "industry_name", "sector", "exclusion_reason")


def load_exclusions(path: Path = REFERENCE_PATH) -> pd.DataFrame:
    """Load the versioned industry exclusion list."""
    return pd.read_csv(path, dtype={"industry_id": int})


def _exclusion_reason(*, industry_name: str, sector: str) -> str | None:
    if industry_name == "Banks":
        return "bank"
    if "Insurance" in industry_name:
        return "insurer"
    if sector == "Utilities":
        return "utility"
    return None


def build_exclusions(industries: pd.DataFrame) -> pd.DataFrame:
    """Select banks, insurers, and utilities from a SimFin industries table."""
    rows: list[dict[str, object]] = []
    for industry_id, row in industries.iterrows():
        industry_name = str(row["Industry"])
        sector = str(row["Sector"])
        reason = _exclusion_reason(industry_name=industry_name, sector=sector)
        if reason is None:
            continue
        rows.append(
            {
                "industry_id": int(industry_id),
                "industry_name": industry_name,
                "sector": sector,
                "exclusion_reason": reason,
            }
        )
    return pd.DataFrame(rows, columns=list(EXCLUSION_COLUMNS)).sort_values("industry_id")


def write_exclusions(df: pd.DataFrame, path: Path = REFERENCE_PATH) -> Path:
    """Persist exclusions CSV (sorted, stable column order)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values("industry_id").to_csv(path, index=False)
    return path
