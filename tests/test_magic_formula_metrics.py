"""Hermetic tests for ROC/EY metric computation (issue #44)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from smartwealthai.compute_metrics import cli_run, format_metrics_table
from smartwealthai.magic_formula_metrics import (
    FORMULA_VERSION,
    build_metrics,
    compute_ev,
    compute_ey,
    compute_market_cap,
    compute_nwc,
    compute_roc,
    compute_total_debt,
)
from smartwealthai.normalize_simfin import cli_run as normalize_cli_run
from smartwealthai.pit_fundamentals import MetricsInputError, compute_metrics_for_ticker
from smartwealthai.price_ingest import run_price_ingest
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)

# AAPL fixture values (SimFin bulk snapshot in tests/fixtures/lake).
AAPL_EBIT = 123_216_000_000.0
AAPL_CURRENT_ASSETS = 152_987_000_000.0
AAPL_CURRENT_LIABILITIES = 176_000_000_000.0
AAPL_CASH = 29_943_000_000.0
AAPL_SHORT_TERM_DEBT = 0.0
AAPL_PPE_NET = 45_680_000_000.0
AAPL_LONG_TERM_DEBT = 95_281_000_000.0
AAPL_SHARES = 15_115_800_000.0
AAPL_ADJ_CLOSE = 273.5
AAPL_NWC = 0.0
AAPL_ROC_DENOM = AAPL_PPE_NET
AAPL_ROC = AAPL_EBIT / AAPL_ROC_DENOM
AAPL_MARKET_CAP = AAPL_SHARES * AAPL_ADJ_CLOSE
AAPL_TOTAL_DEBT = AAPL_LONG_TERM_DEBT
AAPL_EV = AAPL_MARKET_CAP + AAPL_TOTAL_DEBT - AAPL_CASH
AAPL_EY = AAPL_EBIT / AAPL_EV


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    """Curated lake with fundamentals, universe, and prices for AAPL."""
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    root = tmp_path / "lake"
    build_universe(root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    normalize_cli_run(
        [
            "--data-dir",
            str(root),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--universe-run-date",
            RUN_DATE.isoformat(),
        ]
    )
    run_price_ingest(data_dir=root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    return root


def test_compute_nwc_floors_at_zero() -> None:
    nwc = compute_nwc(
        current_assets=100.0,
        cash=30.0,
        current_liabilities=90.0,
        short_term_debt=5.0,
    )
    assert nwc == 0.0


def test_compute_nwc_positive_when_operating_capital_positive() -> None:
    nwc = compute_nwc(
        current_assets=200.0,
        cash=20.0,
        current_liabilities=80.0,
        short_term_debt=10.0,
    )
    assert nwc == 110.0


def test_compute_roc_returns_none_for_non_positive_denominator() -> None:
    assert compute_roc(ebit=100.0, roc_denominator=0.0) is None


def test_compute_ey_returns_none_for_non_positive_ev() -> None:
    assert compute_ey(ebit=100.0, ev=0.0) is None


def test_compute_total_debt_sums_long_and_short_term() -> None:
    assert compute_total_debt(long_term_debt=80.0, short_term_debt=20.0) == 100.0


def test_compute_market_cap_multiplies_shares_by_adj_close() -> None:
    assert compute_market_cap(shares_outstanding=10.0, adj_close=25.5) == 255.0


def test_compute_ev_follows_greenblatt_v1() -> None:
    ev = compute_ev(
        market_cap=1_000.0,
        total_debt=200.0,
        preferred_equity=50.0,
        minority_interest=10.0,
        cash=100.0,
    )
    assert ev == 1_160.0


def test_build_metrics_aapl_fixture_values() -> None:
    result = build_metrics(
        ticker="AAPL",
        ebit=AAPL_EBIT,
        current_assets=AAPL_CURRENT_ASSETS,
        current_liabilities=AAPL_CURRENT_LIABILITIES,
        cash=AAPL_CASH,
        short_term_debt=AAPL_SHORT_TERM_DEBT,
        net_fixed_assets=AAPL_PPE_NET,
        shares_outstanding=AAPL_SHARES,
        adj_close=AAPL_ADJ_CLOSE,
        long_term_debt=AAPL_LONG_TERM_DEBT,
        preferred_equity=0.0,
        minority_interest=0.0,
    )

    assert result.formula_version == FORMULA_VERSION
    assert result.nwc == AAPL_NWC
    assert result.roc_denominator == pytest.approx(AAPL_ROC_DENOM)
    assert result.roc == pytest.approx(AAPL_ROC)
    assert result.market_cap == pytest.approx(AAPL_MARKET_CAP)
    assert result.ev == pytest.approx(AAPL_EV)
    assert result.ey == pytest.approx(AAPL_EY)
    assert result.flags == []


def test_build_metrics_flags_invalid_roc_denominator() -> None:
    result = build_metrics(
        ticker="BAD",
        ebit=100.0,
        current_assets=10.0,
        current_liabilities=10.0,
        cash=10.0,
        short_term_debt=0.0,
        net_fixed_assets=0.0,
        shares_outstanding=1.0,
        adj_close=10.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )

    assert result.roc is None
    assert "invalid_roc_denominator" in result.flags


def test_build_metrics_flags_negative_ebit_and_skips_ey() -> None:
    result = build_metrics(
        ticker="LOSS",
        ebit=-50.0,
        current_assets=200.0,
        current_liabilities=80.0,
        cash=20.0,
        short_term_debt=0.0,
        net_fixed_assets=100.0,
        shares_outstanding=10.0,
        adj_close=25.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )

    assert result.roc == pytest.approx(-50.0 / 200.0)
    assert result.ey is None
    assert result.flags == ["negative_ebit"]


def test_build_metrics_flags_missing_inputs() -> None:
    result = build_metrics(
        ticker="X",
        ebit=None,
        current_assets=1.0,
        current_liabilities=1.0,
        cash=1.0,
        short_term_debt=0.0,
        net_fixed_assets=1.0,
        shares_outstanding=1.0,
        adj_close=1.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )

    assert result.roc is None
    assert result.ey is None
    assert result.flags == ["missing_inputs"]


def test_build_metrics_defaults_null_preferred_and_minority_to_zero() -> None:
    result = build_metrics(
        ticker="AAPL",
        ebit=AAPL_EBIT,
        current_assets=AAPL_CURRENT_ASSETS,
        current_liabilities=AAPL_CURRENT_LIABILITIES,
        cash=AAPL_CASH,
        short_term_debt=AAPL_SHORT_TERM_DEBT,
        net_fixed_assets=AAPL_PPE_NET,
        shares_outstanding=AAPL_SHARES,
        adj_close=AAPL_ADJ_CLOSE,
        long_term_debt=AAPL_LONG_TERM_DEBT,
        preferred_equity=None,
        minority_interest=None,
    )

    assert result.ev == pytest.approx(AAPL_EV)
    assert result.flags == []


def test_compute_metrics_for_ticker_end_to_end(lake: Path) -> None:
    result = compute_metrics_for_ticker(lake, ticker="AAPL", as_of_date=RUN_DATE)

    assert result.ticker == "AAPL"
    assert result.roc == pytest.approx(AAPL_ROC)
    assert result.ey == pytest.approx(AAPL_EY)


def test_compute_metrics_raises_when_fundamentals_missing(lake: Path) -> None:
    with pytest.raises(MetricsInputError, match="not in universe"):
        compute_metrics_for_ticker(lake, ticker="MISSING", as_of_date=RUN_DATE)


def test_format_metrics_table_includes_components() -> None:
    result = build_metrics(
        ticker="AAPL",
        ebit=AAPL_EBIT,
        current_assets=AAPL_CURRENT_ASSETS,
        current_liabilities=AAPL_CURRENT_LIABILITIES,
        cash=AAPL_CASH,
        short_term_debt=AAPL_SHORT_TERM_DEBT,
        net_fixed_assets=AAPL_PPE_NET,
        shares_outstanding=AAPL_SHARES,
        adj_close=AAPL_ADJ_CLOSE,
        long_term_debt=AAPL_LONG_TERM_DEBT,
        preferred_equity=0.0,
        minority_interest=0.0,
    )
    table = format_metrics_table(result)

    assert "Formula version: v1" in table
    assert "ROC:" in table
    assert "EY:" in table


def test_cli_compute_metrics_succeeds_for_aapl(lake: Path) -> None:
    exit_code = cli_run(
        [
            "--ticker",
            "AAPL",
            "--data-dir",
            str(lake),
            "--as-of-date",
            RUN_DATE.isoformat(),
        ]
    )
    assert exit_code == 0


def test_cli_exits_nonzero_when_ticker_missing(lake: Path) -> None:
    exit_code = cli_run(
        [
            "--ticker",
            "MISSING",
            "--data-dir",
            str(lake),
            "--as-of-date",
            RUN_DATE.isoformat(),
        ]
    )
    assert exit_code == 1


def test_compute_metrics_entry_point_registered() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "smartwealthai.compute_metrics", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--ticker" in result.stdout
