"""Demo universe construction from SimFin raw lake snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.lake_paths import (
    curated_exclusions_path,
    curated_universe_path,
    pad_cik,
    simfin_bulk_path,
)
from smartwealthai.simfin_industry_exclusions import REFERENCE_PATH, load_exclusions

UNIVERSE_COLUMNS: tuple[str, ...] = (
    "run_date",
    "ticker",
    "cik",
    "industry_id",
    "sector",
    "market_cap_usd",
)
EXCLUSION_COLUMNS: tuple[str, ...] = (
    "run_date",
    "ticker",
    "cik",
    "industry_id",
    "sector",
    "exclusion_reason",
)


@dataclass
class BuildUniverseResult:
    """Outcome of one universe build run."""

    universe_path: Path
    exclusions_path: Path
    universe_rows: int
    exclusion_rows: int


def build_universe(
    data_dir: Path,
    *,
    run_date: date,
    snapshot_date: date | None = None,
    exclusions_path: Path = REFERENCE_PATH,
) -> BuildUniverseResult:
    """Build the demo investable universe and exclusion log for ``run_date``."""
    effective_snapshot = snapshot_date or run_date
    companies = _load_companies(data_dir, snapshot_date=effective_snapshot)
    industry_sectors = _load_industry_sectors(data_dir, snapshot_date=effective_snapshot)
    excluded_industries = load_exclusions(exclusions_path).set_index("industry_id")
    bank_tickers = _load_statement_tickers(
        data_dir, snapshot_date=effective_snapshot, dataset="income_banks"
    )
    insurance_tickers = _load_statement_tickers(
        data_dir, snapshot_date=effective_snapshot, dataset="income_insurance"
    )

    universe_rows: list[dict[str, object]] = []
    exclusion_rows: list[dict[str, object]] = []

    for _, row in companies.sort_values("Ticker").iterrows():
        if pd.isna(row["Ticker"]) or not str(row["Ticker"]).strip():
            continue
        ticker = str(row["Ticker"]).upper()
        raw_industry_id = row["IndustryId"]
        industry_id = int(raw_industry_id) if pd.notna(raw_industry_id) else None
        sector = _resolve_sector(
            industry_id,
            industry_sectors=industry_sectors,
            excluded_industries=excluded_industries,
        )
        base = {
            "run_date": run_date.isoformat(),
            "ticker": ticker,
            "cik": pad_cik(str(row["CIK"])) if pd.notna(row["CIK"]) else None,
            "industry_id": industry_id,
            "sector": sector,
        }
        if industry_id is not None and industry_id in excluded_industries.index:
            exclusion_rows.append(
                {
                    **base,
                    "exclusion_reason": str(
                        excluded_industries.loc[industry_id, "exclusion_reason"]
                    ),
                }
            )
            continue
        if ticker in bank_tickers:
            exclusion_rows.append({**base, "exclusion_reason": "bank_sanity"})
            continue
        if ticker in insurance_tickers:
            exclusion_rows.append({**base, "exclusion_reason": "insurance_sanity"})
            continue
        universe_rows.append({**base, "market_cap_usd": None})

    universe_df = pd.DataFrame(universe_rows, columns=list(UNIVERSE_COLUMNS))
    exclusions_df = pd.DataFrame(exclusion_rows, columns=list(EXCLUSION_COLUMNS))

    universe_out = curated_universe_path(data_dir, run_date=run_date)
    exclusions_out = curated_exclusions_path(data_dir, run_date=run_date)
    universe_out.parent.mkdir(parents=True, exist_ok=True)
    exclusions_out.parent.mkdir(parents=True, exist_ok=True)

    universe_df.to_parquet(universe_out, index=False)
    exclusions_df.to_parquet(exclusions_out, index=False)

    return BuildUniverseResult(
        universe_path=universe_out,
        exclusions_path=exclusions_out,
        universe_rows=len(universe_df),
        exclusion_rows=len(exclusions_df),
    )


def _load_companies(data_dir: Path, *, snapshot_date: date) -> pd.DataFrame:
    path = simfin_bulk_path(
        data_dir,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=snapshot_date,
    )
    return pd.read_csv(path, sep=";", dtype={"CIK": "string", "IndustryId": "Int64"})


def _load_industry_sectors(data_dir: Path, *, snapshot_date: date) -> dict[int, str]:
    path = simfin_bulk_path(
        data_dir,
        dataset="industries",
        variant=None,
        market=None,
        as_of_date=snapshot_date,
    )
    if not path.exists():
        return {}
    industries = pd.read_csv(path, sep=";", dtype={"IndustryId": "Int64"})
    return {
        int(row["IndustryId"]): str(row["Sector"])
        for _, row in industries.iterrows()
        if pd.notna(row["IndustryId"])
    }


def _resolve_sector(
    industry_id: int | None,
    *,
    industry_sectors: dict[int, str],
    excluded_industries: pd.DataFrame,
) -> str | None:
    if industry_id is None:
        return None
    if industry_id in industry_sectors:
        return industry_sectors[industry_id]
    if industry_id in excluded_industries.index:
        return str(excluded_industries.loc[industry_id, "sector"])
    return None


def _load_statement_tickers(
    data_dir: Path,
    *,
    snapshot_date: date,
    dataset: str,
) -> frozenset[str]:
    path = simfin_bulk_path(
        data_dir,
        dataset=dataset,
        variant=None,
        market="us",
        as_of_date=snapshot_date,
    )
    if not path.exists():
        return frozenset()
    tickers = pd.read_csv(path, sep=";", usecols=["Ticker"])["Ticker"]
    return frozenset(str(ticker).upper() for ticker in tickers)
