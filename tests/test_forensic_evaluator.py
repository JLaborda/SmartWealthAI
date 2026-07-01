"""Hermetic tests for the forensic evaluator orchestrator (issue #89)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from smartwealthai.distress_rules import EXCLUSION_COLUMNS
from smartwealthai.forensic_evaluator import run_forensic_evaluator
from smartwealthai.lake_paths import (
    curated_fundamentals_path,
    curated_permanent_loss_exclusions_path,
    curated_universe_path,
    pad_cik,
)
from smartwealthai.run_forensic_evaluator import cli_run

RUN_DATE = date(2026, 6, 18)
CIK = pad_cik("9999001")


def _write_universe(lake: Path, *, rows: list[dict[str, object]]) -> None:
    path = curated_universe_path(lake, run_date=RUN_DATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_fundamentals(lake: Path, *, period: str, row: dict[str, object]) -> None:
    path = curated_fundamentals_path(lake, cik=CIK, period=period)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_parquet(path, index=False)


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
