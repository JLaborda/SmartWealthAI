"""Bankruptcy / distress hard-exclusion rules for the permanent-loss filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RuleStatus = Literal["pass", "exclude", "unavailable"]

EDGAR_FRAUD_RULE_IDS: tuple[str, ...] = (
    "FRD_RESTATEMENT_RECENT",
    "FRD_AUDITOR_CHANGE_REPEATED",
    "FRD_LATE_FILER",
    "FRD_REGULANTORY_ACTION",
)


@dataclass(frozen=True)
class DistressInputs:
    """Point-in-time inputs for distress rule evaluation."""

    total_assets: float | None = None
    total_liabilities: float | None = None
    stockholders_equity: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    retained_earnings: float | None = None
    ebit: float | None = None
    revenue: float | None = None
    interest_expense: float | None = None
    cash: float | None = None
    short_term_debt: float | None = None
    long_term_debt: float | None = None
    depreciation_amortization: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    market_cap: float | None = None
    listing_status: str | None = None
    delisting_reason: str | None = None


@dataclass(frozen=True)
class RuleEvaluation:
    """Outcome of one forensic / distress rule."""

    rule_id: str
    rule_version: str
    subfilter: str
    status: RuleStatus
    triggered_value: float | None
    threshold: float | None
    explanation: str


EXCLUSION_COLUMNS: tuple[str, ...] = (
    "cik",
    "ticker",
    "subfilter",
    "rule_id",
    "rule_version",
    "triggered_value",
    "threshold",
    "as_of_date",
    "explanation",
)

BK_RULE_VERSION = "distress_rules_v1"
FRAUD_RULE_VERSION = "fraud_rules_v1"
DELIST_REASONS = frozenset({"bankruptcy", "regulatory"})


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
    except TypeError:
        return None
    return float(value)


def distress_inputs_from_row(
    fundamentals: object,
    *,
    market_cap: float | None = None,
    listing_status: str | None = None,
    delisting_reason: str | None = None,
) -> DistressInputs:
    """Build distress inputs from a curated fundamentals row."""

    def get(name: str) -> float | None:
        if hasattr(fundamentals, "get"):
            return _optional_float(fundamentals.get(name))
        return _optional_float(getattr(fundamentals, name, None))

    total_assets = get("total_assets")
    total_liabilities = get("total_liabilities")
    equity = get("stockholders_equity")
    if equity is None and total_assets is not None and total_liabilities is not None:
        equity = total_assets - total_liabilities

    return DistressInputs(
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        stockholders_equity=equity,
        current_assets=get("current_assets"),
        current_liabilities=get("current_liabilities"),
        retained_earnings=get("retained_earnings"),
        ebit=get("ebit"),
        revenue=get("revenue"),
        interest_expense=get("interest_expense"),
        cash=get("cash"),
        short_term_debt=get("short_term_debt"),
        long_term_debt=get("long_term_debt"),
        depreciation_amortization=get("depreciation_amortization"),
        operating_cash_flow=get("operating_cash_flow"),
        capex=get("capex"),
        market_cap=market_cap,
        listing_status=listing_status,
        delisting_reason=delisting_reason,
    )


def evaluate_negative_equity(inputs: DistressInputs, *, config: dict) -> RuleEvaluation:
    """Exclude when stockholders equity is below the configured threshold."""
    threshold = float(config["rules"]["BK_NEGATIVE_EQUITY"]["threshold"])
    equity = inputs.stockholders_equity
    if equity is None:
        return RuleEvaluation(
            rule_id="BK_NEGATIVE_EQUITY",
            rule_version=BK_RULE_VERSION,
            subfilter="bankruptcy",
            status="unavailable",
            triggered_value=None,
            threshold=threshold,
            explanation="missing stockholders_equity",
        )
    status: RuleStatus = "exclude" if equity < threshold else "pass"
    return RuleEvaluation(
        rule_id="BK_NEGATIVE_EQUITY",
        rule_version=BK_RULE_VERSION,
        subfilter="bankruptcy",
        status=status,
        triggered_value=equity,
        threshold=threshold,
        explanation=f"stockholders_equity={equity:.4f}",
    )


def compute_altman_z(inputs: DistressInputs) -> float | None:
    """Return Altman Z for non-financials, or None when required inputs are missing."""
    required = (
        inputs.current_assets,
        inputs.current_liabilities,
        inputs.retained_earnings,
        inputs.ebit,
        inputs.total_assets,
        inputs.total_liabilities,
        inputs.market_cap,
        inputs.revenue,
    )
    if any(value is None for value in required):
        return None
    assert inputs.total_assets is not None
    assert inputs.total_liabilities is not None
    if inputs.total_assets == 0 or inputs.total_liabilities == 0:
        return None

    working_capital = inputs.current_assets - inputs.current_liabilities
    ta = inputs.total_assets
    tl = inputs.total_liabilities
    return (
        1.2 * (working_capital / ta)
        + 1.4 * (inputs.retained_earnings / ta)
        + 3.3 * (inputs.ebit / ta)
        + 0.6 * (inputs.market_cap / tl)
        + 1.0 * (inputs.revenue / ta)
    )


def evaluate_altman_z(inputs: DistressInputs, *, config: dict) -> RuleEvaluation:
    """Exclude when Altman Z is below the distress threshold."""
    threshold = float(config["rules"]["BK_ALTMAN_Z"]["threshold"])
    z_score = compute_altman_z(inputs)
    if z_score is None:
        return RuleEvaluation(
            rule_id="BK_ALTMAN_Z",
            rule_version=BK_RULE_VERSION,
            subfilter="bankruptcy",
            status="unavailable",
            triggered_value=None,
            threshold=threshold,
            explanation="missing Altman Z inputs",
        )
    status: RuleStatus = "exclude" if z_score < threshold else "pass"
    return RuleEvaluation(
        rule_id="BK_ALTMAN_Z",
        rule_version=BK_RULE_VERSION,
        subfilter="bankruptcy",
        status=status,
        triggered_value=z_score,
        threshold=threshold,
        explanation=f"altman_z={z_score:.4f}",
    )


def evaluate_interest_coverage(inputs: DistressInputs, *, config: dict) -> RuleEvaluation:
    """Exclude when EBIT / interest expense is below threshold."""
    threshold = float(config["rules"]["BK_INT_COVERAGE"]["threshold"])
    if inputs.ebit is None or inputs.interest_expense is None:
        return RuleEvaluation(
            rule_id="BK_INT_COVERAGE",
            rule_version=BK_RULE_VERSION,
            subfilter="bankruptcy",
            status="unavailable",
            triggered_value=None,
            threshold=threshold,
            explanation="missing ebit or interest_expense",
        )
    if inputs.interest_expense == 0:
        coverage = float("inf")
    else:
        coverage = inputs.ebit / inputs.interest_expense
    status: RuleStatus = "exclude" if coverage < threshold else "pass"
    return RuleEvaluation(
        rule_id="BK_INT_COVERAGE",
        rule_version=BK_RULE_VERSION,
        subfilter="bankruptcy",
        status=status,
        triggered_value=coverage if coverage != float("inf") else None,
        threshold=threshold,
        explanation=f"interest_coverage={coverage:.4f}",
    )


def _net_debt(inputs: DistressInputs) -> float | None:
    if inputs.cash is None:
        return None
    debt = (inputs.short_term_debt or 0.0) + (inputs.long_term_debt or 0.0)
    return debt - inputs.cash


def _ebitda(inputs: DistressInputs) -> float | None:
    if inputs.ebit is None or inputs.depreciation_amortization is None:
        return None
    return inputs.ebit + inputs.depreciation_amortization


def _free_cash_flow(inputs: DistressInputs) -> float | None:
    if inputs.operating_cash_flow is None:
        return None
    capex = inputs.capex or 0.0
    return inputs.operating_cash_flow - capex


def evaluate_net_debt_ebitda(inputs: DistressInputs, *, config: dict) -> RuleEvaluation:
    """Exclude when net debt / EBITDA exceeds threshold with negative FCF."""
    rule_cfg = config["rules"]["BK_NETDEBT_EBITDA"]
    threshold = float(rule_cfg["net_debt_ebitda_threshold"])
    require_negative_fcf = bool(rule_cfg.get("require_negative_fcf", True))

    net_debt = _net_debt(inputs)
    ebitda = _ebitda(inputs)
    fcf = _free_cash_flow(inputs)
    if net_debt is None or ebitda is None or ebitda == 0:
        return RuleEvaluation(
            rule_id="BK_NETDEBT_EBITDA",
            rule_version=BK_RULE_VERSION,
            subfilter="bankruptcy",
            status="unavailable",
            triggered_value=None,
            threshold=threshold,
            explanation="missing net debt or EBITDA inputs",
        )
    ratio = net_debt / ebitda
    fires = ratio > threshold and (not require_negative_fcf or (fcf is not None and fcf < 0))
    if fcf is None and require_negative_fcf:
        return RuleEvaluation(
            rule_id="BK_NETDEBT_EBITDA",
            rule_version=BK_RULE_VERSION,
            subfilter="bankruptcy",
            status="unavailable",
            triggered_value=ratio,
            threshold=threshold,
            explanation="missing free cash flow",
        )
    status: RuleStatus = "exclude" if fires else "pass"
    return RuleEvaluation(
        rule_id="BK_NETDEBT_EBITDA",
        rule_version=BK_RULE_VERSION,
        subfilter="bankruptcy",
        status=status,
        triggered_value=ratio,
        threshold=threshold,
        explanation=f"net_debt_ebitda={ratio:.4f}",
    )


def evaluate_delisted(inputs: DistressInputs) -> RuleEvaluation:
    """Exclude when listing status is delisted for bankruptcy or regulatory reasons."""
    if inputs.listing_status is None:
        return RuleEvaluation(
            rule_id="BK_DELISTED",
            rule_version=BK_RULE_VERSION,
            subfilter="bankruptcy",
            status="unavailable",
            triggered_value=None,
            threshold=None,
            explanation="missing listing_status",
        )
    normalized_status = inputs.listing_status.lower()
    reason = (inputs.delisting_reason or "").lower()
    fires = normalized_status == "delisted" and reason in DELIST_REASONS
    status: RuleStatus = "exclude" if fires else "pass"
    return RuleEvaluation(
        rule_id="BK_DELISTED",
        rule_version=BK_RULE_VERSION,
        subfilter="bankruptcy",
        status=status,
        triggered_value=None,
        threshold=None,
        explanation=f"listing_status={inputs.listing_status}, delisting_reason={reason or 'none'}",
    )


def evaluate_edgar_fraud_rule(rule_id: str) -> RuleEvaluation:
    """Return unavailable for EDGAR-dependent fraud rules until data is wired."""
    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=FRAUD_RULE_VERSION,
        subfilter="fraud",
        status="unavailable",
        triggered_value=None,
        threshold=None,
        explanation="edgar data not available",
    )


def evaluate_distress_rules(inputs: DistressInputs, *, config: dict) -> list[RuleEvaluation]:
    """Evaluate all bankruptcy / distress hard rules."""
    return [
        evaluate_negative_equity(inputs, config=config),
        evaluate_altman_z(inputs, config=config),
        evaluate_interest_coverage(inputs, config=config),
        evaluate_net_debt_ebitda(inputs, config=config),
        evaluate_delisted(inputs),
    ]


def evaluate_fraud_rules(*, edgar_available: bool = False) -> list[RuleEvaluation]:
    """Evaluate fraud rules; EDGAR rules are unavailable until wired."""
    rule_ids = (
        "FRD_RESTATEMENT_RECENT",
        "FRD_AUDITOR_CHANGE_REPEATED",
        "FRD_LATE_FILER",
        "FRD_REGULATORY_ACTION",
    )
    if edgar_available:
        # ponytail: EDGAR wiring deferred; same unavailable path until implemented
        pass
    return [evaluate_edgar_fraud_rule(rule_id) for rule_id in rule_ids]
