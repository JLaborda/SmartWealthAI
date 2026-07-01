"""CI regression: Enron, Lehman, WorldCom must be excluded at documented distress dates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from smartwealthai.distress_rules import evaluate_distress_rules
from smartwealthai.lake_paths import pad_cik
from smartwealthai.permanent_loss_config import load_distress_rules_config

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "permanent_loss"


@dataclass(frozen=True)
class RegressionCase:
    name: str
    ticker: str
    cik: str
    decision_date: date
    fundamentals: dict[str, float]


REGRESSION_CASES: tuple[RegressionCase, ...] = (
    RegressionCase(
        name="Enron Q3 2001",
        ticker="ENRN",
        cik=pad_cik("1024401"),
        decision_date=date(2001, 11, 15),
        fundamentals={
            "current_assets": 10_000.0,
            "current_liabilities": 25_000.0,
            "retained_earnings": -20_000.0,
            "ebit": -500.0,
            "total_assets": 40_000.0,
            "total_liabilities": 45_000.0,
            "revenue": 30_000.0,
            "stockholders_equity": -5_000.0,
            "interest_expense": 800.0,
            "cash": 500.0,
            "short_term_debt": 8_000.0,
            "long_term_debt": 15_000.0,
            "depreciation_amortization": 200.0,
            "operating_cash_flow": -1_000.0,
        },
    ),
    RegressionCase(
        name="Lehman Q2 2008",
        ticker="LEH",
        cik=pad_cik("806085"),
        decision_date=date(2008, 9, 15),
        fundamentals={
            "current_assets": 50_000.0,
            "current_liabilities": 120_000.0,
            "retained_earnings": -5_000.0,
            "ebit": -200.0,
            "total_assets": 600_000.0,
            "total_liabilities": 650_000.0,
            "revenue": 10_000.0,
            "stockholders_equity": -50_000.0,
            "interest_expense": 2_000.0,
            "cash": 2_000.0,
            "short_term_debt": 100_000.0,
            "long_term_debt": 150_000.0,
            "depreciation_amortization": 500.0,
            "operating_cash_flow": -5_000.0,
        },
    ),
    RegressionCase(
        name="WorldCom Q1 2002",
        ticker="MCWE",
        cik=pad_cik("723527"),
        decision_date=date(2002, 5, 15),
        fundamentals={
            "current_assets": 8_000.0,
            "current_liabilities": 15_000.0,
            "retained_earnings": -30_000.0,
            "ebit": -1_000.0,
            "total_assets": 100_000.0,
            "total_liabilities": 110_000.0,
            "revenue": 20_000.0,
            "stockholders_equity": -10_000.0,
            "interest_expense": 1_500.0,
            "cash": 1_000.0,
            "short_term_debt": 12_000.0,
            "long_term_debt": 20_000.0,
            "depreciation_amortization": 800.0,
            "operating_cash_flow": -2_000.0,
        },
    ),
)


@pytest.mark.parametrize("case", REGRESSION_CASES, ids=[case.name for case in REGRESSION_CASES])
def test_distress_regression_case_is_excluded(case: RegressionCase) -> None:
    """Each historical bankruptcy case must trip at least one hard distress rule."""
    from smartwealthai.distress_rules import distress_inputs_from_row

    inputs = distress_inputs_from_row(case.fundamentals, market_cap=1_000.0)
    results = evaluate_distress_rules(inputs, config=load_distress_rules_config())
    excluded = [result for result in results if result.status == "exclude"]
    assert excluded, f"{case.name} ({case.ticker}) must be excluded by distress rules"


def test_regression_fixture_manifest_exists() -> None:
    manifest = FIXTURE_DIR / "cases.json"
    assert manifest.exists()
    frame = pd.read_json(manifest)
    assert len(frame) == 3
