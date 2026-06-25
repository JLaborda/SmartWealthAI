"""Greenblatt-style ROC and Earnings Yield (formula v1)."""

from __future__ import annotations

from dataclasses import dataclass, field

FORMULA_VERSION = "v1"


@dataclass
class MetricsResult:
    """ROC/EY breakdown for one ticker on one decision date."""

    ticker: str
    formula_version: str = FORMULA_VERSION
    ebit: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    cash: float | None = None
    short_term_debt: float | None = None
    nwc: float | None = None
    net_fixed_assets: float | None = None
    roc_denominator: float | None = None
    roc: float | None = None
    shares_outstanding: float | None = None
    adj_close: float | None = None
    market_cap: float | None = None
    long_term_debt: float | None = None
    total_debt: float | None = None
    preferred_equity: float | None = None
    minority_interest: float | None = None
    ev: float | None = None
    ey: float | None = None
    flags: list[str] = field(default_factory=list)


def compute_nwc(
    *,
    current_assets: float,
    cash: float,
    current_liabilities: float,
    short_term_debt: float,
) -> float:
    """Net working capital per Greenblatt v1 (floored at zero)."""
    raw = current_assets - cash - current_liabilities + short_term_debt
    return max(raw, 0.0)


def compute_total_debt(*, long_term_debt: float, short_term_debt: float) -> float:
    """Total debt = long-term + short-term (v1; no capital leases in mapping)."""
    return long_term_debt + short_term_debt


def compute_market_cap(*, shares_outstanding: float, adj_close: float) -> float:
    """Market cap from shares outstanding and adjusted close."""
    return shares_outstanding * adj_close


def compute_ev(
    *,
    market_cap: float,
    total_debt: float,
    preferred_equity: float,
    minority_interest: float,
    cash: float,
) -> float:
    """Enterprise value per Greenblatt v1."""
    return market_cap + total_debt + preferred_equity + minority_interest - cash


def compute_roc(*, ebit: float, roc_denominator: float) -> float | None:
    """Return on capital; None when denominator is not positive."""
    if roc_denominator <= 0:
        return None
    return ebit / roc_denominator


def compute_ey(*, ebit: float, ev: float) -> float | None:
    """Earnings yield; None when EV is not positive."""
    if ev <= 0:
        return None
    return ebit / ev


def _coalesce(value: float | None, default: float = 0.0) -> float:
    return default if value is None else value


def build_metrics(
    *,
    ticker: str,
    ebit: float | None,
    current_assets: float | None,
    current_liabilities: float | None,
    cash: float | None,
    short_term_debt: float | None,
    net_fixed_assets: float | None,
    shares_outstanding: float | None,
    adj_close: float | None,
    long_term_debt: float | None,
    preferred_equity: float | None,
    minority_interest: float | None,
) -> MetricsResult:
    """Assemble a full ROC/EY result with validation flags."""
    result = MetricsResult(
        ticker=ticker,
        ebit=ebit,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        cash=cash,
        short_term_debt=short_term_debt,
        net_fixed_assets=net_fixed_assets,
        shares_outstanding=shares_outstanding,
        adj_close=adj_close,
        long_term_debt=long_term_debt,
        preferred_equity=preferred_equity,
        minority_interest=minority_interest,
    )

    required = {
        "ebit": ebit,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "cash": cash,
        "short_term_debt": short_term_debt,
        "net_fixed_assets": net_fixed_assets,
        "shares_outstanding": shares_outstanding,
        "adj_close": adj_close,
        "long_term_debt": long_term_debt,
        "preferred_equity": preferred_equity,
        "minority_interest": minority_interest,
    }
    if any(value is None for value in required.values()):
        result.flags.append("missing_inputs")
        return result

    if ebit < 0:
        result.flags.append("negative_ebit")

    result.nwc = compute_nwc(
        current_assets=current_assets,
        cash=cash,
        current_liabilities=current_liabilities,
        short_term_debt=short_term_debt,
    )
    result.roc_denominator = result.nwc + net_fixed_assets
    if result.roc_denominator <= 0:
        result.flags.append("invalid_roc_denominator")
    else:
        result.roc = compute_roc(ebit=ebit, roc_denominator=result.roc_denominator)

    result.total_debt = compute_total_debt(
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
    )
    result.market_cap = compute_market_cap(
        shares_outstanding=shares_outstanding,
        adj_close=adj_close,
    )
    result.ev = compute_ev(
        market_cap=result.market_cap,
        total_debt=result.total_debt,
        preferred_equity=_coalesce(preferred_equity),
        minority_interest=_coalesce(minority_interest),
        cash=cash,
    )
    if result.ev <= 0:
        result.flags.append("invalid_ev")
    elif ebit > 0:
        result.ey = compute_ey(ebit=ebit, ev=result.ev)

    return result
