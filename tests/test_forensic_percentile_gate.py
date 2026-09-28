"""Tests for forensic bottom-percentile gate (issue #89)."""

from __future__ import annotations

from smartwealthai.forensic_percentile_gate import ForensicScore, apply_bottom_percentile_gate


def _score(ticker: str, value: float) -> ForensicScore:
    return ForensicScore(
        ticker=ticker,
        cik=f"cik-{ticker}",
        model="beneish",
        score=value,
        rule_version="beneish_v1",
        market_cap=float(ord(ticker[0])),
    )


def test_bottom_five_percent_excludes_worst_score_among_twenty() -> None:
    scores = [_score(f"T{i:02d}", float(i)) for i in range(20)]
    excluded = apply_bottom_percentile_gate(scores)
    assert len(excluded) == 1
    assert excluded[0].ticker == "T19"
    assert excluded[0].rule_id == "FRD_BENEISH_BOTTOM_PCT"


def test_bottom_gate_returns_empty_for_empty_input() -> None:
    assert apply_bottom_percentile_gate([]) == []
