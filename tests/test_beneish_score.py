"""Tests for Beneish M-Score (issue #89)."""

from __future__ import annotations

import pandas as pd

from smartwealthai.beneish_score import compute_beneish_m_score, missing_beneish_fields


def _period_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "fiscal_period_end": pd.Timestamp("2023-12-31"),
        "accounts_receivable": 100.0,
        "revenue": 1000.0,
        "cost_of_revenue": 600.0,
        "total_assets": 2000.0,
        "ppe_net": 500.0,
        "depreciation_amortization": 50.0,
        "sga_expense": 200.0,
        "net_income": 80.0,
        "operating_cash_flow": 120.0,
        "current_assets": 400.0,
        "current_liabilities": 200.0,
        "long_term_debt": 300.0,
    }
    row.update(overrides)
    return row


def test_beneish_requires_two_periods() -> None:
    history = pd.DataFrame([_period_row()])
    result = compute_beneish_m_score(history)
    assert result.m_score is None
    assert "history" in result.missing_fields


def test_beneish_computes_score_from_two_periods() -> None:
    prior = _period_row(
        fiscal_period_end=pd.Timestamp("2022-12-31"),
        accounts_receivable=90.0,
        revenue=900.0,
        cost_of_revenue=540.0,
        total_assets=1800.0,
        ppe_net=450.0,
        depreciation_amortization=45.0,
        sga_expense=180.0,
        net_income=70.0,
        operating_cash_flow=110.0,
        current_assets=360.0,
        current_liabilities=180.0,
        long_term_debt=280.0,
    )
    current = _period_row(fiscal_period_end=pd.Timestamp("2023-12-31"))
    result = compute_beneish_m_score(pd.DataFrame([prior, current]))
    assert result.m_score is not None
    assert result.rule_version == "beneish_v1"
    assert not result.missing_fields


def test_missing_beneish_fields_detects_absent_columns() -> None:
    row = pd.Series(_period_row())
    row = row.drop("sga_expense")
    missing = missing_beneish_fields(row)
    assert "sga_expense" in missing


def test_missing_beneish_fields_detects_nan_values() -> None:
    row = pd.Series(_period_row(sga_expense=float("nan")))
    missing = missing_beneish_fields(row)
    assert "sga_expense" in missing


def test_beneish_returns_missing_fields_when_prior_period_incomplete() -> None:
    prior = _period_row(fiscal_period_end=pd.Timestamp("2022-12-31"), revenue=float("nan"))
    current = _period_row(fiscal_period_end=pd.Timestamp("2023-12-31"))
    result = compute_beneish_m_score(pd.DataFrame([prior, current]))
    assert result.m_score is None
    assert "revenue" in result.missing_fields


def test_beneish_returns_derived_ratio_when_growth_inputs_invalid() -> None:
    prior = _period_row(
        fiscal_period_end=pd.Timestamp("2022-12-31"),
        revenue=0.0,
        cost_of_revenue=0.0,
    )
    current = _period_row(fiscal_period_end=pd.Timestamp("2023-12-31"), revenue=1000.0)
    result = compute_beneish_m_score(pd.DataFrame([prior, current]))
    assert result.m_score is None
    assert result.missing_fields == ("derived_ratio",)


def test_beneish_returns_derived_ratio_when_depreciation_denominator_zero() -> None:
    prior = _period_row(
        fiscal_period_end=pd.Timestamp("2022-12-31"),
        depreciation_amortization=0.0,
        ppe_net=0.0,
    )
    current = _period_row(
        fiscal_period_end=pd.Timestamp("2023-12-31"),
        depreciation_amortization=0.0,
        ppe_net=0.0,
    )
    result = compute_beneish_m_score(pd.DataFrame([prior, current]))
    assert result.m_score is None
    assert result.missing_fields == ("derived_ratio",)


def test_beneish_returns_derived_ratio_when_total_assets_zero() -> None:
    prior = _period_row(
        fiscal_period_end=pd.Timestamp("2022-12-31"),
        total_assets=0.0,
        current_assets=0.0,
        ppe_net=0.0,
    )
    current = _period_row(
        fiscal_period_end=pd.Timestamp("2023-12-31"),
        total_assets=0.0,
        current_assets=0.0,
        ppe_net=0.0,
    )
    result = compute_beneish_m_score(pd.DataFrame([prior, current]))
    assert result.m_score is None
    assert result.missing_fields == ("derived_ratio",)


def test_missing_beneish_fields_treats_non_comparable_values_as_missing() -> None:
    class NonComparable:
        def __eq__(self, _other: object) -> bool:
            raise TypeError("no compare")

    row = pd.Series(_period_row(sga_expense=NonComparable()))
    missing = missing_beneish_fields(row)
    assert "sga_expense" in missing
