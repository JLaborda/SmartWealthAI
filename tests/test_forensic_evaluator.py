"""Hermetic tests for the forensic evaluator orchestrator (issue #89)."""

from __future__ import annotations

import runpy
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from smartwealthai.distress_rules import EXCLUSION_COLUMNS
from smartwealthai.forensic_evaluator import (
    _load_fundamentals_history,
    _load_latest_fundamentals,
    _load_prices,
    _market_cap,
    run_forensic_evaluator,
)
from smartwealthai.lake_paths import (
    curated_fundamentals_path,
    curated_permanent_loss_exclusions_path,
    curated_prices_snapshot_path,
    curated_universe_path,
    pad_cik,
)
from smartwealthai.run_forensic_evaluator import cli_run, main

RUN_DATE = date(2026, 6, 18)
CIK = pad_cik("9999001")
CIK_B = pad_cik("9999002")
CIK_C = pad_cik("9999003")


def _write_universe(lake: Path, *, rows: list[dict[str, object]]) -> None:
    path = curated_universe_path(lake, run_date=RUN_DATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_fundamentals(
    lake: Path,
    *,
    cik: str = CIK,
    period: str,
    row: dict[str, object],
) -> None:
    path = curated_fundamentals_path(lake, cik=cik, period=period)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_parquet(path, index=False)


def _healthy_fundamentals_row(
    *,
    cik: str,
    ticker: str,
    fiscal_period_end: str,
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "cik": cik,
        "ticker": ticker,
        "as_of_date": pd.Timestamp("2026-06-01"),
        "fiscal_period_end": pd.Timestamp(fiscal_period_end),
        "version_id": 1,
        "statement_variant": "annual",
        "total_assets": 2000.0,
        "total_liabilities": 800.0,
        "stockholders_equity": 1200.0,
        "current_assets": 400.0,
        "current_liabilities": 200.0,
        "retained_earnings": 500.0,
        "ebit": 100.0,
        "revenue": 1000.0,
        "interest_expense": 10.0,
        "cash": 100.0,
        "short_term_debt": 50.0,
        "long_term_debt": 300.0,
        "depreciation_amortization": 50.0,
        "operating_cash_flow": 120.0,
        "capex": 20.0,
        "accounts_receivable": 100.0,
        "cost_of_revenue": 600.0,
        "ppe_net": 500.0,
        "sga_expense": 200.0,
        "net_income": 80.0,
    }
    row.update(overrides)
    return row


def _write_prices_snapshot(lake: Path, *, rows: list[dict[str, object]]) -> None:
    path = curated_prices_snapshot_path(lake, run_date=RUN_DATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    return tmp_path / "lake"


def test_run_forensic_evaluator_writes_exclusion_for_negative_equity(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "DIST",
                "cik": CIK,
                "industry_id": 1,
                "sector": "Technology",
                "market_cap_usd": 100.0,
            }
        ],
    )
    _write_fundamentals(
        lake,
        period="2024Q4",
        row={
            "cik": CIK,
            "ticker": "DIST",
            "as_of_date": pd.Timestamp("2026-06-01"),
            "fiscal_period_end": pd.Timestamp("2024-12-31"),
            "version_id": 1,
            "statement_variant": "annual",
            "total_assets": 100.0,
            "total_liabilities": 150.0,
            "stockholders_equity": -50.0,
            "ebit": 1.0,
            "revenue": 10.0,
            "interest_expense": 5.0,
            "cash": 1.0,
            "short_term_debt": 0.0,
            "long_term_debt": 0.0,
            "depreciation_amortization": 1.0,
            "operating_cash_flow": -2.0,
        },
    )

    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    exclusions = pd.read_parquet(result.exclusions_path)
    assert list(exclusions.columns) == list(EXCLUSION_COLUMNS)
    assert "DIST" in set(exclusions["ticker"])
    assert "BK_NEGATIVE_EQUITY" in set(exclusions["rule_id"])


def test_run_forensic_evaluator_cli_writes_output(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "DIST",
                "cik": CIK,
                "industry_id": 1,
                "sector": "Technology",
                "market_cap_usd": 100.0,
            }
        ],
    )
    _write_fundamentals(
        lake,
        period="2024Q4",
        row={
            "cik": CIK,
            "ticker": "DIST",
            "as_of_date": pd.Timestamp("2026-06-01"),
            "fiscal_period_end": pd.Timestamp("2024-12-31"),
            "version_id": 1,
            "statement_variant": "annual",
            "total_assets": 100.0,
            "total_liabilities": 150.0,
            "stockholders_equity": -50.0,
        },
    )

    exit_code = cli_run(["--data-dir", str(lake), "--run-date", RUN_DATE.isoformat()])
    assert exit_code == 0
    assert curated_permanent_loss_exclusions_path(lake, run_date=RUN_DATE).exists()


def test_market_cap_uses_shares_times_adj_close() -> None:
    fundamentals = pd.Series({"shares_outstanding": 100.0})
    price_row = pd.Series({"adj_close": 12.5})
    assert _market_cap(fundamentals, price_row) == 1250.0


def test_market_cap_falls_back_to_snapshot_market_cap() -> None:
    fundamentals = pd.Series({})
    price_row = pd.Series({"market_cap_usd": 900.0})
    assert _market_cap(fundamentals, price_row) == 900.0


def test_market_cap_none_when_shares_or_price_nan() -> None:
    fundamentals = pd.Series({"shares_outstanding": float("nan")})
    price_row = pd.Series({"adj_close": 10.0})
    assert _market_cap(fundamentals, price_row) is None


def test_market_cap_none_when_price_row_missing() -> None:
    fundamentals = pd.Series({"shares_outstanding": 100.0})
    assert _market_cap(fundamentals, None) is None


def test_load_prices_returns_empty_when_snapshot_missing(lake: Path) -> None:
    assert _load_prices(lake, run_date=RUN_DATE) == {}


def test_load_latest_fundamentals_returns_empty_when_no_partitions(lake: Path) -> None:
    assert _load_latest_fundamentals(lake, ciks={CIK}, as_of_date=RUN_DATE) == {}


def test_load_fundamentals_history_filters_non_annual_quarterly_variants(lake: Path) -> None:
    _write_fundamentals(
        lake,
        period="2024Q4",
        row=_healthy_fundamentals_row(cik=CIK, ticker="GOOD", fiscal_period_end="2024-12-31"),
    )
    _write_fundamentals(
        lake,
        period="2023Q4",
        row=_healthy_fundamentals_row(
            cik=CIK,
            ticker="GOOD",
            fiscal_period_end="2023-12-31",
            statement_variant="ttm",
        ),
    )
    history = _load_fundamentals_history(lake, cik=CIK, as_of_date=RUN_DATE)
    assert len(history) == 1
    assert history.iloc[0]["statement_variant"] == "annual"


def test_run_forensic_evaluator_raises_when_universe_missing(lake: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No universe snapshot"):
        run_forensic_evaluator(lake, run_date=RUN_DATE)


def test_run_forensic_evaluator_routes_missing_cik_to_review_queue(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "NCIK",
                "cik": None,
                "industry_id": 1,
                "sector": "Technology",
            }
        ],
    )

    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    assert result.review_count == 1
    assert result.issues_path is not None
    issues = pd.read_parquet(result.issues_path)
    assert issues.iloc[0]["reason"] == "missing_cik"


def test_run_forensic_evaluator_routes_missing_fundamentals_to_review_queue(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "NOFUND",
                "cik": CIK,
                "industry_id": 1,
                "sector": "Technology",
            }
        ],
    )

    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    assert result.review_count >= 1
    issues = pd.read_parquet(result.issues_path)
    assert "missing_fundamentals" in set(issues["reason"])


def test_run_forensic_evaluator_excludes_delisted_bankruptcy_from_prices(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "DELIST",
                "cik": CIK,
                "industry_id": 1,
                "sector": "Technology",
            }
        ],
    )
    _write_fundamentals(
        lake,
        period="2024Q4",
        row=_healthy_fundamentals_row(cik=CIK, ticker="DELIST", fiscal_period_end="2024-12-31"),
    )
    _write_prices_snapshot(
        lake,
        rows=[
            {
                "ticker": "DELIST",
                "adj_close": 1.0,
                "listing_status": "delisted",
                "delisting_reason": "bankruptcy",
            }
        ],
    )

    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    exclusions = pd.read_parquet(result.exclusions_path)
    assert "BK_DELISTED" in set(exclusions["rule_id"])


def test_run_forensic_evaluator_writes_beneish_percentile_exclusion(lake: Path) -> None:
    tickers = (
        ("GOOD1", CIK, 100.0),
        ("GOOD2", CIK_B, 120.0),
        ("BAD", CIK_C, 500.0),
    )
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": ticker,
                "cik": cik,
                "industry_id": 1,
                "sector": "Technology",
            }
            for ticker, cik, _ in tickers
        ],
    )
    for ticker, cik, receivable in tickers:
        for period, fiscal_end in (("2023Q4", "2023-12-31"), ("2024Q4", "2024-12-31")):
            _write_fundamentals(
                lake,
                cik=cik,
                period=period,
                row=_healthy_fundamentals_row(
                    cik=cik,
                    ticker=ticker,
                    fiscal_period_end=fiscal_end,
                    accounts_receivable=receivable,
                ),
            )
    _write_prices_snapshot(
        lake,
        rows=[
            {
                "ticker": ticker,
                "adj_close": 10.0,
                "shares_outstanding": 10.0,
                "listing_status": pd.NA,
                "delisting_reason": pd.NA,
            }
            for ticker, _, _ in tickers
        ],
    )

    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    exclusions = pd.read_parquet(result.exclusions_path)
    percentile_rows = exclusions.loc[exclusions["rule_id"] == "FRD_BENEISH_BOTTOM_PCT"]
    assert len(percentile_rows) == 1
    assert percentile_rows.iloc[0]["subfilter"] == "forensic_percentile"
    assert result.issues_path is not None
    issues = pd.read_parquet(result.issues_path)
    assert issues["rule_id"].notna().any()


def test_run_forensic_evaluator_routes_missing_beneish_inputs_to_review_queue(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "PART",
                "cik": CIK,
                "industry_id": 1,
                "sector": "Technology",
            }
        ],
    )
    for period, fiscal_end in (("2023Q4", "2023-12-31"), ("2024Q4", "2024-12-31")):
        _write_fundamentals(
            lake,
            period=period,
            row=_healthy_fundamentals_row(
                cik=CIK,
                ticker="PART",
                fiscal_period_end=fiscal_end,
                accounts_receivable=None,
            ),
        )

    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    issues = pd.read_parquet(result.issues_path)
    assert any("missing beneish inputs" in str(reason) for reason in issues["reason"])


def test_run_forensic_evaluator_cli_echoes_review_queue_path(lake: Path) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "NCIK",
                "cik": None,
                "industry_id": 1,
                "sector": "Technology",
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--data-dir", str(lake), "--run-date", RUN_DATE.isoformat()],
    )
    assert result.exit_code == 0
    assert "Review queue:" in result.output


def test_run_forensic_evaluator_main_module_entrypoint(
    lake: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_universe(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "DIST",
                "cik": CIK,
                "industry_id": 1,
                "sector": "Technology",
            }
        ],
    )
    _write_fundamentals(
        lake,
        period="2024Q4",
        row={
            "cik": CIK,
            "ticker": "DIST",
            "as_of_date": pd.Timestamp("2026-06-01"),
            "fiscal_period_end": pd.Timestamp("2024-12-31"),
            "version_id": 1,
            "statement_variant": "annual",
            "stockholders_equity": -50.0,
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run-forensic-evaluator",
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("smartwealthai.run_forensic_evaluator", run_name="__main__")
    assert exc_info.value.code == 0
    assert curated_permanent_loss_exclusions_path(lake, run_date=RUN_DATE).exists()


def test_run_forensic_evaluator_skips_issues_file_when_universe_empty(lake: Path) -> None:
    _write_universe(lake, rows=[])
    result = run_forensic_evaluator(lake, run_date=RUN_DATE)
    assert result.issues_path is None
    assert result.review_count == 0
