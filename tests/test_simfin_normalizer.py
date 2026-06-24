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
    fiscal_period_label,
    simfin_bulk_path,
)
from smartwealthai.normalize_simfin import cli_run
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


def test_normalize_simfin_preserves_same_period_restatement_versions(
    lake_with_simfin: Path,
) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    _append_csv_line(
        income_path,
        "AAPL;111052;2024-09-28;2024-11-01;2025-10-31;USD;2024;Q4;"
        "392000000000;124000000000;94000000000",
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows == 2
    rows = pd.read_parquet(
        curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q4")
    )
    assert set(rows["version_id"]) == {1, 2}
    assert len(rows) == 2


def test_normalize_simfin_stamps_later_balance_publish_date(lake_with_simfin: Path) -> None:
    balance_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="balance",
        variant="quarterly",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    balance_path.write_text(balance_path.read_text().replace("2024-11-01;", "2024-12-15;"))

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows == 1
    row = pd.read_parquet(
        curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q4")
    ).iloc[0]
    as_of = row["as_of_date"]
    as_of_date = as_of.date() if hasattr(as_of, "date") else as_of
    assert as_of_date == date(2024, 12, 15)
    assert row["as_of_source"] == "balance_publish_date"


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


def test_fiscal_period_label_uses_calendar_quarter() -> None:
    assert fiscal_period_label(date(2024, 9, 28)) == "2024Q3"


def test_cli_normalize_simfin_writes_curated_output(lake_with_simfin: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake_with_simfin),
            "--snapshot-date",
            SIMFIN_FIXTURE_DATE.isoformat(),
            "--ticker",
            "AAPL",
        ]
    )

    assert exit_code == 0
    assert curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q4").exists()


def test_normalize_simfin_skips_tickers_outside_filter(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    _append_csv_line(
        income_path,
        "MSFT;222;2024-06-30;2024-07-30;;USD;2024;Q2;211915000000;88520000000;72361000000",
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows == 1
    assert result.issue_rows == 0


def test_normalize_simfin_routes_unknown_ticker_to_issues(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    _append_csv_line(
        income_path,
        "NOPE;999;2024-06-30;2024-07-30;;USD;2024;Q2;100;10;5",
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"NOPE"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert "missing_company_metadata" in set(issues["reason"])


def test_normalize_simfin_routes_missing_cik_to_issues(lake_with_simfin: Path) -> None:
    companies_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    _append_csv_line(companies_path, "NOCIK;999;No CIK Inc.;50;USA;")
    _append_csv_line(
        income_path,
        "NOCIK;999;2024-06-30;2024-07-30;;USD;2024;Q2;100;10;5",
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"NOCIK"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "missing_cik"


def test_normalize_simfin_routes_missing_balance_to_issues(lake_with_simfin: Path) -> None:
    companies_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    _append_csv_line(companies_path, "NOBS;888;No Balance Inc.;50;USA;0000999888")
    _append_csv_line(
        income_path,
        "NOBS;888;2024-06-30;2024-07-30;;USD;2024;Q2;100;10;5",
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"NOBS"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "missing_balance_row"


def test_normalize_simfin_routes_non_usd_currency_to_issues(lake_with_simfin: Path) -> None:
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
            "2024-11-01;;EUR",
        )
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "non_usd_currency"


def test_normalize_simfin_routes_missing_mandatory_fields_to_issues(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path.write_text(income_path.read_text().replace("391035000000;", ";"))

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "missing_mandatory_fields"


def test_normalize_simfin_routes_invalid_cik_to_issues(lake_with_simfin: Path) -> None:
    companies_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    companies_path.write_text(companies_path.read_text().replace("0000320193", "../../evil"))

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    assert result.issue_rows == 1
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "invalid_cik"
    assert list((lake_with_simfin / "curated" / "fundamentals").rglob("fundamentals.parquet")) == []


def test_normalize_simfin_routes_invalid_period_to_issues(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path.write_text(income_path.read_text().replace(";Q4;", ";/..//Q4;"))

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    assert result.issue_rows == 1
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "invalid_period"
    assert list((lake_with_simfin / "curated" / "fundamentals").rglob("fundamentals.parquet")) == []


def test_normalize_simfin_routes_as_of_before_period_end_to_issues(lake_with_simfin: Path) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    balance_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="balance",
        variant="quarterly",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    for path in (income_path, balance_path):
        path.write_text(path.read_text().replace("2024-11-01;", "2024-01-01;"))

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
        run_date=SIMFIN_FIXTURE_DATE,
    )

    assert result.written_rows == 0
    issues = pd.read_parquet(curated_issues_path(lake_with_simfin, run_date=SIMFIN_FIXTURE_DATE))
    assert issues.iloc[0]["reason"] == "as_of_before_period_end"


def test_normalize_simfin_uses_calendar_period_when_fiscal_labels_missing(
    lake_with_simfin: Path,
) -> None:
    income_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    income_path.write_text(
        income_path.read_text().replace("2024;Q4;", ";;").replace("2024;Q4;", ";;")
    )

    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows == 1
    assert curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q3").exists()


def test_load_simfin_mapping_parses_minimal_yaml(tmp_path: Path) -> None:
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        "version: test_v1\n"
        "fields:\n"
        "  ebit: EBIT\n"
        "meta:\n"
        "  ticker: Ticker\n"
        "unknown_section:\n"
        "missing_publish_lag_days: 45\n"
        "note without colon\n"
    )

    mapping = load_simfin_mapping(mapping_path)

    assert mapping["version"] == "test_v1"
    assert mapping["fields"]["ebit"] == "EBIT"
    assert mapping["missing_publish_lag_days"] == 45


def _append_csv_line(path: Path, line: str) -> None:
    path.write_text(path.read_text().rstrip("\n") + "\n" + line + "\n")


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
