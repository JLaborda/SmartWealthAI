"""Read curated lake artifacts for the demo Streamlit dashboard."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.lake_paths import curated_combined_ranking_path, curated_portfolio_path

_RUN_DATE_RE = re.compile(r"run_date=(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class DashboardSnapshot:
    """Curated ranking and portfolio tables for one pipeline run."""

    run_date: date
    ranking: pd.DataFrame
    portfolio: pd.DataFrame
    has_ranking: bool
    has_portfolio: bool


@dataclass(frozen=True)
class OverviewHeadline:
    """Headline stats for the Overview page."""

    run_date: date
    ranked_count: int
    portfolio_count: int
    top_ticker: str | None


def resolve_data_dir() -> Path:
    """Return the lake root from ``SMARTWEALTHAI_DATA_DIR`` (default ``data``)."""
    return Path(os.environ.get("SMARTWEALTHAI_DATA_DIR", "data"))


def discover_latest_run_date(data_dir: Path) -> date | None:
    """Return the newest ``run_date`` partition under curated portfolio."""
    portfolio_root = data_dir / "curated" / "portfolio"
    if not portfolio_root.is_dir():
        return None

    dates: list[date] = []
    for child in portfolio_root.iterdir():
        match = _RUN_DATE_RE.fullmatch(child.name)
        if match and (child / "portfolio.parquet").is_file():
            dates.append(date.fromisoformat(match.group(1)))

    return max(dates) if dates else None


def load_dashboard_snapshot(data_dir: Path, *, run_date: date) -> DashboardSnapshot:
    """Load ranking and portfolio parquet for a run date (empty state if missing)."""
    ranking_path = curated_combined_ranking_path(data_dir, run_date=run_date)
    portfolio_path = curated_portfolio_path(data_dir, run_date=run_date)

    has_ranking = ranking_path.is_file()
    has_portfolio = portfolio_path.is_file()

    ranking = pd.read_parquet(ranking_path) if has_ranking else pd.DataFrame()
    portfolio = pd.read_parquet(portfolio_path) if has_portfolio else pd.DataFrame()

    return DashboardSnapshot(
        run_date=run_date,
        ranking=ranking,
        portfolio=portfolio,
        has_ranking=has_ranking,
        has_portfolio=has_portfolio,
    )


def overview_headline(snapshot: DashboardSnapshot) -> OverviewHeadline:
    """Summarize portfolio headline stats for the Overview page."""
    top_ticker = None
    if snapshot.has_portfolio and not snapshot.portfolio.empty:
        top_ticker = str(snapshot.portfolio.iloc[0]["ticker"])

    return OverviewHeadline(
        run_date=snapshot.run_date,
        ranked_count=len(snapshot.ranking) if snapshot.has_ranking else 0,
        portfolio_count=len(snapshot.portfolio) if snapshot.has_portfolio else 0,
        top_ticker=top_ticker,
    )
