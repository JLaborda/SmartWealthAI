"""Tests for STA, SNOA, and COMBOACCRUAL accrual metrics (issue #89)."""

from __future__ import annotations

import pandas as pd

from smartwealthai.accrual_scores import (
    build_comboaccrual_forensic_scores,
    compute_accrual_metrics,
    compute_snoa,
    compute_sta,
    missing_accrual_fields,
)


def _fundamentals_row(**overrides: object) -> pd.Series:
    row: dict[str, object] = {
        "net_income": 80.0,
        "operating_cash_flow": 120.0,
        "total_assets": 2000.0,
        "cash": 100.0,
        "total_liabilities": 800.0,
        "short_term_debt": 50.0,
        "long_term_debt": 300.0,
    }
    row.update(overrides)
    return pd.Series(row)


def test_compute_sta_is_net_income_minus_cfo_over_assets() -> None:
    row = _fundamentals_row()
    assert compute_sta(row) == (80.0 - 120.0) / 2000.0


def test_compute_snoa_uses_operating_assets_minus_liabilities() -> None:
    row = _fundamentals_row()
    operating_assets = 2000.0 - 100.0
    operating_liabilities = 800.0 - 50.0 - 300.0
    assert compute_snoa(row) == (operating_assets - operating_liabilities) / 2000.0


def test_compute_snoa_uses_lagged_total_assets_when_provided() -> None:
    row = _fundamentals_row()
    operating_assets = 2000.0 - 100.0
    operating_liabilities = 800.0 - 50.0 - 300.0
    assert (
        compute_snoa(row, lagged_total_assets=1600.0)
        == (operating_assets - operating_liabilities) / 1600.0
    )


def test_missing_accrual_fields_detects_required_columns() -> None:
    row = _fundamentals_row(cash=None)
    missing = missing_accrual_fields(row)
    assert "cash" in missing


def test_compute_accrual_metrics_returns_sta_and_snoa() -> None:
    current = _fundamentals_row()
    prior = _fundamentals_row(total_assets=1800.0)
    result = compute_accrual_metrics(current, prior_row=prior)
    assert result.sta is not None
    assert result.snoa is not None
    assert result.rule_version == "accrual_v1"
    assert not result.missing_fields


def test_build_comboaccrual_forensic_scores_averages_percentiles() -> None:
    candidates = [
        (
            "LOW",
            "cik-low",
            compute_accrual_metrics(_fundamentals_row(net_income=50.0, operating_cash_flow=120.0)),
            1.0,
        ),
        (
            "HIGH",
            "cik-high",
            compute_accrual_metrics(_fundamentals_row(net_income=500.0, operating_cash_flow=120.0)),
            2.0,
        ),
    ]
    scores = build_comboaccrual_forensic_scores(candidates)
    assert len(scores) == 2
    by_ticker = {row.ticker: row.score for row in scores}
    assert by_ticker["HIGH"] > by_ticker["LOW"]
    assert all(row.model == "comboaccrual" for row in scores)
