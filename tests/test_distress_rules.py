"""Tests for bankruptcy / distress rule evaluators (issue #89)."""

from __future__ import annotations

from dataclasses import dataclass

from smartwealthai.distress_rules import (
    DistressInputs,
    compute_altman_z,
    distress_inputs_from_row,
    evaluate_altman_z,
    evaluate_delisted,
    evaluate_distress_rules,
    evaluate_edgar_fraud_rule,
    evaluate_fraud_rules,
    evaluate_interest_coverage,
    evaluate_negative_equity,
    evaluate_net_debt_ebitda,
)
from smartwealthai.permanent_loss_config import load_distress_rules_config


def _distress_config() -> dict:
    return load_distress_rules_config()


def test_negative_equity_excludes_when_equity_below_threshold() -> None:
    inputs = DistressInputs(stockholders_equity=-1.0)
    result = evaluate_negative_equity(inputs, config=_distress_config())
    assert result.status == "exclude"
    assert result.rule_id == "BK_NEGATIVE_EQUITY"
    assert result.triggered_value == -1.0


def test_negative_equity_passes_when_equity_positive() -> None:
    inputs = DistressInputs(stockholders_equity=100.0)
    result = evaluate_negative_equity(inputs, config=_distress_config())
    assert result.status == "pass"


def test_negative_equity_unavailable_when_equity_missing() -> None:
    result = evaluate_negative_equity(DistressInputs(), config=_distress_config())
    assert result.status == "unavailable"


def test_distress_inputs_derives_equity_from_assets_minus_liabilities() -> None:
    row = {"total_assets": 100.0, "total_liabilities": 120.0}
    inputs = distress_inputs_from_row(row)
    assert inputs.stockholders_equity == -20.0


def test_altman_z_excludes_distressed_company() -> None:
    inputs = DistressInputs(
        current_assets=10.0,
        current_liabilities=50.0,
        retained_earnings=-80.0,
        ebit=-5.0,
        total_assets=100.0,
        total_liabilities=150.0,
        market_cap=5.0,
        revenue=20.0,
    )
    z_score = compute_altman_z(inputs)
    assert z_score is not None
    assert z_score < 1.81
    result = evaluate_altman_z(inputs, config=_distress_config())
    assert result.status == "exclude"


def test_altman_z_passes_healthy_company() -> None:
    inputs = DistressInputs(
        current_assets=80.0,
        current_liabilities=20.0,
        retained_earnings=50.0,
        ebit=30.0,
        total_assets=200.0,
        total_liabilities=40.0,
        market_cap=500.0,
        revenue=300.0,
    )
    result = evaluate_altman_z(inputs, config=_distress_config())
    assert result.status == "pass"


def test_interest_coverage_excludes_when_below_one() -> None:
    inputs = DistressInputs(ebit=0.5, interest_expense=1.0)
    result = evaluate_interest_coverage(inputs, config=_distress_config())
    assert result.status == "exclude"
    assert result.triggered_value == 0.5


def test_net_debt_ebitda_excludes_high_leverage_with_negative_fcf() -> None:
    inputs = DistressInputs(
        cash=1.0,
        short_term_debt=20.0,
        long_term_debt=60.0,
        ebit=2.0,
        depreciation_amortization=2.0,
        operating_cash_flow=-5.0,
        capex=0.0,
    )
    result = evaluate_net_debt_ebitda(inputs, config=_distress_config())
    assert result.status == "exclude"
    assert result.triggered_value == 19.75


def test_delisted_excludes_bankruptcy_delisting() -> None:
    inputs = DistressInputs(listing_status="delisted", delisting_reason="bankruptcy")
    result = evaluate_delisted(inputs)
    assert result.status == "exclude"


def test_delisted_passes_active_listing() -> None:
    inputs = DistressInputs(listing_status="active")
    result = evaluate_delisted(inputs)
    assert result.status == "pass"


def test_edgar_fraud_rules_are_unavailable_without_edgar() -> None:
    results = evaluate_fraud_rules(edgar_available=False)
    assert len(results) == 4
    assert all(result.status == "unavailable" for result in results)


def test_evaluate_edgar_fraud_rule_never_excludes() -> None:
    result = evaluate_edgar_fraud_rule("FRD_REGULATORY_ACTION")
    assert result.status == "unavailable"


def test_evaluate_distress_rules_returns_all_bankruptcy_rules() -> None:
    inputs = DistressInputs(stockholders_equity=10.0, listing_status="active")
    results = evaluate_distress_rules(inputs, config=_distress_config())
    rule_ids = {result.rule_id for result in results}
    assert rule_ids == {
        "BK_NEGATIVE_EQUITY",
        "BK_ALTMAN_Z",
        "BK_INT_COVERAGE",
        "BK_NETDEBT_EBITDA",
        "BK_DELISTED",
    }


def test_distress_inputs_reads_attributes_when_row_has_no_get() -> None:
    @dataclass
    class FundamentalsRow:
        total_assets: float
        total_liabilities: float
        ebit: float

    inputs = distress_inputs_from_row(FundamentalsRow(100.0, 40.0, 5.0))
    assert inputs.stockholders_equity == 60.0
    assert inputs.ebit == 5.0


def test_distress_inputs_treats_nan_as_missing() -> None:
    row = {"total_assets": float("nan"), "stockholders_equity": 10.0}
    inputs = distress_inputs_from_row(row)
    assert inputs.total_assets is None
    assert inputs.stockholders_equity == 10.0


def test_distress_inputs_treats_non_comparable_values_as_missing() -> None:
    class NonComparable:
        def __eq__(self, _other: object) -> bool:
            raise TypeError("no compare")

    row = {"total_assets": NonComparable(), "stockholders_equity": 10.0}
    inputs = distress_inputs_from_row(row)
    assert inputs.total_assets is None


def test_altman_z_none_when_total_assets_zero() -> None:
    inputs = DistressInputs(
        current_assets=10.0,
        current_liabilities=5.0,
        retained_earnings=1.0,
        ebit=1.0,
        total_assets=0.0,
        total_liabilities=1.0,
        market_cap=10.0,
        revenue=5.0,
    )
    assert compute_altman_z(inputs) is None
    result = evaluate_altman_z(inputs, config=_distress_config())
    assert result.status == "unavailable"


def test_interest_coverage_passes_when_interest_expense_zero() -> None:
    inputs = DistressInputs(ebit=10.0, interest_expense=0.0)
    result = evaluate_interest_coverage(inputs, config=_distress_config())
    assert result.status == "pass"
    assert result.triggered_value is None


def test_interest_coverage_unavailable_when_ebit_missing() -> None:
    result = evaluate_interest_coverage(
        DistressInputs(interest_expense=1.0),
        config=_distress_config(),
    )
    assert result.status == "unavailable"


def test_net_debt_ebitda_passes_when_leverage_acceptable() -> None:
    inputs = DistressInputs(
        cash=50.0,
        short_term_debt=10.0,
        long_term_debt=20.0,
        ebit=100.0,
        depreciation_amortization=10.0,
        operating_cash_flow=80.0,
        capex=10.0,
    )
    result = evaluate_net_debt_ebitda(inputs, config=_distress_config())
    assert result.status == "pass"


def test_net_debt_ebitda_unavailable_when_fcf_missing() -> None:
    inputs = DistressInputs(
        cash=1.0,
        short_term_debt=20.0,
        long_term_debt=60.0,
        ebit=2.0,
        depreciation_amortization=2.0,
        operating_cash_flow=None,
    )
    result = evaluate_net_debt_ebitda(inputs, config=_distress_config())
    assert result.status == "unavailable"
    assert result.triggered_value == 19.75


def test_delisted_unavailable_when_listing_status_missing() -> None:
    result = evaluate_delisted(DistressInputs())
    assert result.status == "unavailable"


def test_delisted_excludes_regulatory_delisting() -> None:
    inputs = DistressInputs(listing_status="delisted", delisting_reason="regulatory")
    result = evaluate_delisted(inputs)
    assert result.status == "exclude"


def test_delisted_passes_non_bankruptcy_delisting() -> None:
    inputs = DistressInputs(listing_status="delisted", delisting_reason="merger")
    result = evaluate_delisted(inputs)
    assert result.status == "pass"


def test_evaluate_fraud_rules_with_edgar_available_still_unavailable() -> None:
    results = evaluate_fraud_rules(edgar_available=True)
    assert len(results) == 4
    assert all(result.status == "unavailable" for result in results)
