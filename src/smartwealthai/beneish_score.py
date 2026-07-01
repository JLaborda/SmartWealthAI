"""Beneish M-Score computation from multi-period PIT fundamentals."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from smartwealthai.permanent_loss_config import load_beneish_config

BENEISH_REQUIRED_FIELDS: tuple[str, ...] = (
    "accounts_receivable",
    "revenue",
    "cost_of_revenue",
    "total_assets",
    "ppe_net",
    "depreciation_amortization",
    "sga_expense",
    "net_income",
    "operating_cash_flow",
    "current_assets",
    "current_liabilities",
    "long_term_debt",
)


@dataclass(frozen=True)
class BeneishResult:
    """Outcome of a Beneish M-Score calculation."""

    m_score: float | None
    rule_version: str
    missing_fields: tuple[str, ...]


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        if value != value:
            return None
    except TypeError:
        return None
    return float(value)


def _row_value(row: pd.Series, field: str) -> float | None:
    return _optional_float(row.get(field))


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _gross_margin(revenue: float | None, cost_of_revenue: float | None) -> float | None:
    if revenue is None or cost_of_revenue is None or revenue == 0:
        return None
    return (revenue - cost_of_revenue) / revenue


def _asset_quality_index(
    *,
    current_assets: float | None,
    ppe_net: float | None,
    total_assets: float | None,
) -> float | None:
    if current_assets is None or ppe_net is None or total_assets is None or total_assets == 0:
        return None
    return 1.0 - (current_assets + ppe_net) / total_assets


def _depi(depreciation: float | None, ppe_net: float | None) -> float | None:
    if depreciation is None or ppe_net is None:
        return None
    denom = depreciation + ppe_net
    if denom == 0:
        return None
    return depreciation / denom


def missing_beneish_fields(row: pd.Series) -> tuple[str, ...]:
    """Return canonical fields missing from one fundamentals row."""
    return tuple(field for field in BENEISH_REQUIRED_FIELDS if _row_value(row, field) is None)


def compute_beneish_m_score(
    history: pd.DataFrame,
    *,
    config: dict | None = None,
) -> BeneishResult:
    """Compute Beneish M-Score from at least two fiscal periods of PIT history."""
    cfg = config or load_beneish_config()
    version = str(cfg["version"])
    if len(history) < 2:
        return BeneishResult(m_score=None, rule_version=version, missing_fields=("history",))

    ordered = history.sort_values("fiscal_period_end")
    current = ordered.iloc[-1]
    prior = ordered.iloc[-2]

    missing = missing_beneish_fields(current) + missing_beneish_fields(prior)
    if missing:
        return BeneishResult(
            m_score=None,
            rule_version=version,
            missing_fields=tuple(dict.fromkeys(missing)),
        )

    recv_t = _row_value(current, "accounts_receivable")
    recv_p = _row_value(prior, "accounts_receivable")
    sales_t = _row_value(current, "revenue")
    sales_p = _row_value(prior, "revenue")
    dsri = _safe_ratio(
        _safe_ratio(recv_t, sales_t),
        _safe_ratio(recv_p, sales_p),
    )

    gm_t = _gross_margin(sales_t, _row_value(current, "cost_of_revenue"))
    gm_p = _gross_margin(sales_p, _row_value(prior, "cost_of_revenue"))
    gmi = _safe_ratio(gm_p, gm_t)

    aqi_t = _asset_quality_index(
        current_assets=_row_value(current, "current_assets"),
        ppe_net=_row_value(current, "ppe_net"),
        total_assets=_row_value(current, "total_assets"),
    )
    aqi_p = _asset_quality_index(
        current_assets=_row_value(prior, "current_assets"),
        ppe_net=_row_value(prior, "ppe_net"),
        total_assets=_row_value(prior, "total_assets"),
    )
    aqi = _safe_ratio(aqi_t, aqi_p)

    sgi = _safe_ratio(sales_t, sales_p)

    depi = _safe_ratio(
        _depi(_row_value(prior, "depreciation_amortization"), _row_value(prior, "ppe_net")),
        _depi(_row_value(current, "depreciation_amortization"), _row_value(current, "ppe_net")),
    )

    sgai = _safe_ratio(
        _safe_ratio(_row_value(current, "sga_expense"), sales_t),
        _safe_ratio(_row_value(prior, "sga_expense"), sales_p),
    )

    net_income = _row_value(current, "net_income")
    cfo = _row_value(current, "operating_cash_flow")
    total_assets = _row_value(current, "total_assets")
    tata = _safe_ratio(
        (net_income - cfo) if net_income is not None and cfo is not None else None,
        total_assets,
    )

    def leverage(row: pd.Series) -> float | None:
        ltd = _row_value(row, "long_term_debt") or 0.0
        cl = _row_value(row, "current_liabilities") or 0.0
        ta = _row_value(row, "total_assets")
        return _safe_ratio(ltd + cl, ta)

    lvgi = _safe_ratio(leverage(current), leverage(prior))

    components = (dsri, gmi, aqi, sgi, depi, sgai, tata, lvgi)
    if any(value is None for value in components):
        return BeneishResult(
            m_score=None,
            rule_version=version,
            missing_fields=("derived_ratio",),
        )

    coeffs = cfg["coefficients"]
    m_score = (
        float(cfg["intercept"])
        + float(coeffs["dsri"]) * dsri
        + float(coeffs["gmi"]) * gmi
        + float(coeffs["aqi"]) * aqi
        + float(coeffs["sgi"]) * sgi
        + float(coeffs["depi"]) * depi
        + float(coeffs["sgai"]) * sgai
        + float(coeffs["tata"]) * tata
        + float(coeffs["lvgi"]) * lvgi
    )
    return BeneishResult(m_score=m_score, rule_version=version, missing_fields=())
