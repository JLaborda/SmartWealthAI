"""STA, SNOA, and COMBOACCRUAL forensic accrual metrics (QVAL Ch. 3)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from smartwealthai.forensic_percentile_gate import ForensicScore
from smartwealthai.permanent_loss_config import load_accrual_config

STA_REQUIRED_FIELDS: tuple[str, ...] = ("net_income", "operating_cash_flow", "total_assets")
SNOA_REQUIRED_FIELDS: tuple[str, ...] = (
    "total_assets",
    "cash",
    "total_liabilities",
    "short_term_debt",
    "long_term_debt",
)


@dataclass(frozen=True)
class AccrualMetrics:
    """Point-in-time STA and SNOA for one issuer."""

    sta: float | None
    snoa: float | None
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


def missing_accrual_fields(row: pd.Series) -> tuple[str, ...]:
    """Return canonical fields missing for STA or SNOA on one row."""
    missing = [field for field in STA_REQUIRED_FIELDS if _row_value(row, field) is None]
    missing.extend(field for field in SNOA_REQUIRED_FIELDS if _row_value(row, field) is None)
    return tuple(dict.fromkeys(missing))


def compute_sta(row: pd.Series) -> float | None:
    """Scaled total accruals: (net income - operating cash flow) / total assets."""
    net_income = _row_value(row, "net_income")
    operating_cash_flow = _row_value(row, "operating_cash_flow")
    total_assets = _row_value(row, "total_assets")
    if net_income is None or operating_cash_flow is None:
        return None
    return _safe_ratio(net_income - operating_cash_flow, total_assets)


def compute_snoa(row: pd.Series, *, lagged_total_assets: float | None = None) -> float | None:
    """Scaled net operating assets per Gray/Carlisle (QVAL Ch. 3)."""
    total_assets = _row_value(row, "total_assets")
    cash = _row_value(row, "cash")
    total_liabilities = _row_value(row, "total_liabilities")
    short_term_debt = _row_value(row, "short_term_debt") or 0.0
    long_term_debt = _row_value(row, "long_term_debt") or 0.0
    if total_assets is None or cash is None or total_liabilities is None:
        return None

    operating_assets = total_assets - cash
    operating_liabilities = total_liabilities - short_term_debt - long_term_debt
    denominator = lagged_total_assets if lagged_total_assets is not None else total_assets
    return _safe_ratio(operating_assets - operating_liabilities, denominator)


def compute_accrual_metrics(
    row: pd.Series,
    *,
    prior_row: pd.Series | None = None,
    config: dict | None = None,
) -> AccrualMetrics:
    """Compute STA and SNOA for the latest PIT fundamentals row."""
    cfg = config or load_accrual_config()
    version = str(cfg["version"])
    missing = missing_accrual_fields(row)
    if missing:
        return AccrualMetrics(sta=None, snoa=None, rule_version=version, missing_fields=missing)

    lagged_assets = _row_value(prior_row, "total_assets") if prior_row is not None else None
    sta = compute_sta(row)
    snoa = compute_snoa(row, lagged_total_assets=lagged_assets)
    if sta is None or snoa is None:
        return AccrualMetrics(
            sta=sta,
            snoa=snoa,
            rule_version=version,
            missing_fields=("derived_ratio",),
        )
    return AccrualMetrics(sta=sta, snoa=snoa, rule_version=version, missing_fields=())


def _percentile_rank_higher_is_worse(values: dict[str, float]) -> dict[str, float]:
    """Map ticker -> percentile in [0, 1]; higher raw value -> higher percentile."""
    if not values:
        return {}
    if len(values) == 1:
        return {next(iter(values)): 0.5}

    ordered = sorted(values.items(), key=lambda item: item[1])
    ranks: dict[str, float] = {}
    index = 0
    count = len(ordered)
    while index < count:
        end = index
        while end + 1 < count and ordered[end + 1][1] == ordered[index][1]:
            end += 1
        avg_rank = (index + end) / 2.0
        percentile = avg_rank / (count - 1)
        for offset in range(index, end + 1):
            ranks[ordered[offset][0]] = percentile
        index = end + 1
    return ranks


def build_comboaccrual_forensic_scores(
    candidates: list[tuple[str, str, AccrualMetrics, float]],
) -> list[ForensicScore]:
    """Build COMBOACCRUAL scores as the average STA/SNOA cross-sectional percentiles."""
    scored: list[tuple[str, str, float, str, float]] = []
    sta_values: dict[str, float] = {}
    snoa_values: dict[str, float] = {}

    for ticker, cik, metrics, market_cap in candidates:
        if metrics.sta is None or metrics.snoa is None:
            continue
        sta_values[ticker] = metrics.sta
        snoa_values[ticker] = metrics.snoa
        scored.append((ticker, cik, market_cap, metrics.rule_version, 0.0))

    if not scored:
        return []

    sta_percentiles = _percentile_rank_higher_is_worse(sta_values)
    snoa_percentiles = _percentile_rank_higher_is_worse(snoa_values)
    return [
        ForensicScore(
            ticker=ticker,
            cik=cik,
            model="comboaccrual",
            score=(sta_percentiles[ticker] + snoa_percentiles[ticker]) / 2.0,
            rule_version=rule_version,
            market_cap=market_cap,
        )
        for ticker, cik, market_cap, rule_version, _ in scored
    ]
