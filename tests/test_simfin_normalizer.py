"""Hermetic tests for the SimFin fundamentals normalizer (issue #57)."""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import click
import pandas as pd
import pytest

from smartwealthai.fixture_lake import FIXTURES_DIR
from smartwealthai.lake_paths import (
    curated_fundamentals_path,
    curated_issues_path,
    fiscal_period_label,
    simfin_bulk_path,
)
from smartwealthai.normalize_simfin import (
    cli_run,
    load_universe_tickers,
    resolve_show_progress,
)
from smartwealthai.simfin_normalizer import (
    DEFAULT_MAPPING_PATH,
    _index_balance_by_ticker,
    _latest_balance_row,
    _raw_paths,
    _read_simfin_csv,
    _resolve_show_progress,
    _work_tickers,
    load_simfin_mapping,
    normalize_simfin,
)
from smartwealthai.universe_builder import build_universe

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


def test_fiscal_period_label_uses_calendar_quarter() -> None:
    assert fiscal_period_label(date(2024, 9, 28)) == "2024Q3"


def test_cli_normalize_simfin_requires_scope(lake_with_simfin: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake_with_simfin),
            "--snapshot-date",
            SIMFIN_FIXTURE_DATE.isoformat(),
        ]
    )

    assert exit_code != 0


def test_work_tickers_intersects_scoped_set(lake_with_simfin: Path) -> None:
    income = _read_simfin_csv(_raw_paths(lake_with_simfin, SIMFIN_FIXTURE_DATE)["income"])
    work = _work_tickers(income, ticker_col="Ticker", tickers={"AAPL", "MISSING"})
    assert work == ["AAPL"]


def test_work_tickers_returns_all_income_tickers_when_unscoped(lake_with_simfin: Path) -> None:
    income = _read_simfin_csv(_raw_paths(lake_with_simfin, SIMFIN_FIXTURE_DATE)["income"])
    work = _work_tickers(income, ticker_col="Ticker", tickers=None)
    assert work == ["AAPL", "BAR", "FOO", "LOST", "MSFT"]


def test_work_tickers_logs_skipped_scoped_tickers(
    lake_with_simfin: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    income = _read_simfin_csv(_raw_paths(lake_with_simfin, SIMFIN_FIXTURE_DATE)["income"])

    with caplog.at_level(logging.INFO, logger="smartwealthai.simfin_normalizer"):
        _work_tickers(income, ticker_col="Ticker", tickers={"AAPL", "GHOST", "MISSING"})

    assert "scoped ticker(s) have no income rows" in caplog.text


def test_resolve_show_progress_autodetects_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    assert _resolve_show_progress(None) is True
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    assert _resolve_show_progress(None) is False


def test_normalize_show_progress_flags_map_to_cli_helpers() -> None:
    assert resolve_show_progress(progress=False, quiet=True) is False
    assert resolve_show_progress(progress=True, quiet=False) is True


def test_load_universe_tickers_raises_click_exception_when_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match="Universe not found"):
        load_universe_tickers(tmp_path, SIMFIN_FIXTURE_DATE)


def test_latest_balance_row_returns_none_when_report_date_before_all(
    lake_with_simfin: Path,
) -> None:
    paths = _raw_paths(lake_with_simfin, SIMFIN_FIXTURE_DATE)
    balance = _read_simfin_csv(paths["balance"])
    indexed = _index_balance_by_ticker(
        balance,
        ticker_col="Ticker",
        report_col="Report Date",
    )

    row = _latest_balance_row(
        indexed,
        ticker="AAPL",
        report_date=pd.Timestamp("2020-01-01"),
        report_col="Report Date",
    )

    assert row is None


def _add_msft_rows(lake_with_simfin: Path) -> None:
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
    balance_path = simfin_bulk_path(
        lake_with_simfin,
        dataset="balance",
        variant="quarterly",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    _append_csv_line(companies_path, "MSFT;222;Microsoft Corp.;50;USA;0000789019")
    _append_csv_line(
        income_path,
        "MSFT;222;2024-06-30;2024-07-30;;USD;2024;Q2;211915000000;88520000000;72361000000",
    )
    _append_csv_line(
        balance_path,
        "MSFT;222;2024-06-30;2024-07-30;;USD;2024;Q2;"
        "120000000000;90000000000;20000000000;0;30000000000;50000000000;0;0;"
        "500000000000;200000000000;7500000000",
    )


def test_normalize_simfin_writes_multiple_partitions_with_progress(
    lake_with_simfin: Path,
) -> None:
    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL", "MSFT"},
        show_progress=True,
    )

    assert result.written_rows == 2
    assert curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q4").exists()
    assert curated_fundamentals_path(lake_with_simfin, cik="0000789019", period="2024Q4").exists()


def test_normalize_simfin_writes_multiple_partitions_without_progress(
    lake_with_simfin: Path,
) -> None:
    result = normalize_simfin(
        lake_with_simfin,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL", "MSFT"},
        show_progress=False,
    )

    assert result.written_rows == 2


def test_cli_progress_and_quiet_mutually_exclusive(lake_with_simfin: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake_with_simfin),
            "--snapshot-date",
            SIMFIN_FIXTURE_DATE.isoformat(),
            "--ticker",
            "AAPL",
            "--progress",
            "--quiet",
        ]
    )
    assert exit_code != 0


def test_normalize_simfin_with_universe_run_date(lake_with_simfin: Path) -> None:
    build_universe(
        lake_with_simfin,
        run_date=SIMFIN_FIXTURE_DATE,
        snapshot_date=SIMFIN_FIXTURE_DATE,
    )

    exit_code = cli_run(
        [
            "--data-dir",
            str(lake_with_simfin),
            "--snapshot-date",
            SIMFIN_FIXTURE_DATE.isoformat(),
            "--universe-run-date",
            SIMFIN_FIXTURE_DATE.isoformat(),
        ]
    )

    assert exit_code == 0
    assert curated_fundamentals_path(lake_with_simfin, cik="0000320193", period="2024Q4").exists()


def test_load_universe_tickers_reads_curated_snapshot(lake_with_simfin: Path) -> None:
    build_universe(
        lake_with_simfin,
        run_date=SIMFIN_FIXTURE_DATE,
        snapshot_date=SIMFIN_FIXTURE_DATE,
    )

    tickers = load_universe_tickers(lake_with_simfin, SIMFIN_FIXTURE_DATE)

    assert "AAPL" in tickers


def test_balance_index_returns_same_row_as_full_scan(lake_with_simfin: Path) -> None:
    paths = _raw_paths(lake_with_simfin, SIMFIN_FIXTURE_DATE)
    balance = _read_simfin_csv(paths["balance"])
    indexed = _index_balance_by_ticker(
        balance,
        ticker_col="Ticker",
        report_col="Report Date",
    )
    report_date = pd.Timestamp("2024-09-28")
    row = _latest_balance_row(
        indexed,
        ticker="AAPL",
        report_date=report_date,
        report_col="Report Date",
    )
    naive = (
        balance.loc[(balance["Ticker"] == "AAPL") & (balance["Report Date"] <= report_date)]
        .sort_values("Report Date")
        .iloc[-1]
    )

    assert row is not None
    assert row["Total Assets"] == naive["Total Assets"]


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


def test_load_simfin_mapping_parses_qv_required_fields() -> None:
    mapping = load_simfin_mapping(DEFAULT_MAPPING_PATH)

    assert "accounts_receivable" in mapping["qv_required_fields"]
    assert mapping["fields"]["operating_cash_flow"] == "Net Cash from Operating Activities"


def test_normalize_simfin_writes_quarterly_qv_fields(tmp_path: Path) -> None:
    _copy_simfin_fixtures(tmp_path, include_multiperiod=True)

    result = normalize_simfin(
        tmp_path,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.written_rows >= 2
    output = curated_fundamentals_path(tmp_path, cik="0000320193", period="2024Q4")
    quarterly = (
        pd.read_parquet(output).loc[lambda frame: frame["statement_variant"] == "quarterly"].iloc[0]
    )
    assert quarterly["accounts_receivable"] == 33_410_000_000
    assert quarterly["operating_cash_flow"] == 118_254_000_000


def test_normalize_simfin_routes_missing_qv_inputs_to_issues(tmp_path: Path) -> None:
    _copy_simfin_fixtures(tmp_path, include_multiperiod=True)
    cashflow_path = simfin_bulk_path(
        tmp_path,
        dataset="cashflow",
        variant="quarterly",
        market="us",
        as_of_date=SIMFIN_FIXTURE_DATE,
    )
    cashflow_path.unlink()

    result = normalize_simfin(
        tmp_path,
        snapshot_date=SIMFIN_FIXTURE_DATE,
        tickers={"AAPL"},
    )

    assert result.issue_rows >= 1
    issues = pd.read_parquet(curated_issues_path(tmp_path, run_date=SIMFIN_FIXTURE_DATE))
    assert "missing_qv_inputs" in set(issues["reason"])


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


_SKIP_UNLESS_MULTIPERIOD = (
    "dataset=income/variant=quarterly/",
    "dataset=income/variant=annual/",
    "dataset=balance/variant=annual/",
    "dataset=cashflow/variant=annual/",
    "dataset=cashflow/variant=quarterly/",
)


def _copy_simfin_fixtures(data_dir: Path, *, include_multiperiod: bool = False) -> None:
    src = FIXTURES_DIR / "raw" / "simfin"
    dst = data_dir / "raw" / "simfin"
    for path in src.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src)
            rel_str = f"{rel.parent}/"
            if not include_multiperiod and any(
                marker in rel_str for marker in _SKIP_UNLESS_MULTIPERIOD
            ):
                continue
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


@pytest.fixture
def lake_with_simfin(tmp_path: Path) -> Path:
    _copy_simfin_fixtures(tmp_path)
    return tmp_path
