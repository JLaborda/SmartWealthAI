"""Hermetic tests for the SimFin fundamentals normalizer (issue #57)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from smartwealthai.fixture_lake import FIXTURES_DIR
from smartwealthai.lake_paths import (
    curated_fundamentals_path,
    curated_issues_path,
    simfin_bulk_path,
)
from smartwealthai.simfin_normalizer import (
    DEFAULT_MAPPING_PATH,
    load_simfin_mapping,
    normalize_simfin,
)

SIMFIN_FIXTURE_DATE = date(2026, 6, 18)


def test_load_simfin_mapping_exposes_canonical_field_names() -> None:
    mapping = load_simfin_mapping(DEFAULT_MAPPING_PATH)

    assert mapping["version"] == "simfin_mapping_v1"
    assert mapping["fields"]["ebit"] == "Operating Income (Loss)"
    assert mapping["meta"]["publish_date"] == "Publish Date"


def test_normalize_simfin_maps_one_ticker_to_curated_pit_row(tmp_path: Path) -> None:
    _copy_simfin_fixtures(tmp_path)

    result = normalize_simfin(
        tmp_path,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows == 1
    assert result.issue_rows == 0

    output = curated_fundamentals_path(
        tmp_path,
        cik="0000320193",
        period="2024Q4",
    )
    assert output.exists()

    row = pd.read_parquet(output).iloc[0]
    assert row["ticker"] == "AAPL"
    assert row["cik"] == "0000320193"
    assert row["ebit"] == 123_216_000_000
    as_of = row["as_of_date"]
    as_of_date = as_of.date() if hasattr(as_of, "date") else as_of
    assert as_of_date == date(2024, 11, 1)
    assert row["version_id"] == 1
    fiscal_end = row["fiscal_period_end"]
    fiscal_period_end = fiscal_end.date() if hasattr(fiscal_end, "date") else fiscal_end
    assert fiscal_period_end == date(2024, 9, 28)
    assert row["mapping_version"] == "simfin_mapping_v1"


def test_normalize_simfin_uses_restated_date_for_new_version(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path.write_text(
        income_path.read_text().replace(
            "2024-11-01;;USD",
            "2024-11-01;2025-10-31;USD",
        )
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows == 1
    row = pd.read_parquet(
        curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q4")
    ).iloc[0]
    assert row["version_id"] == 2
    as_of = row["as_of_date"]
    as_of_date = as_of.date() if hasattr(as_of, "date") else as_of
    assert as_of_date == date(2025, 10, 31)


def test_normalize_simfin_routes_missing_publish_date_to_issues(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path.write_text(income_path.read_text().replace("2024-11-01;", ";"))

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    assert result.issue_rows == 1
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "missing_publish_date"


def _copy_simfin_fixtures(data_dir: Path) -> None:
    src = FIXTURES_DIR / "raw" / "simfin"
    dst = data_dir / "raw" / "simfin"
    for path in src.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


@pytest.fixture
def lake_with_simfin(tmp_path: Path) -> Path:
    _copy_simfin_fixtures(tmp_path)
    return tmp_path
