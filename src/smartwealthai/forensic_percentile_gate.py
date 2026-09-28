"""Cross-sectional forensic percentile gate (QVAL-style bottom exclusion)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from smartwealthai.permanent_loss_config import load_forensic_gate_config


@dataclass(frozen=True)
class ForensicScore:
    """One continuous forensic model score for percentile ranking."""

    ticker: str
    cik: str
    model: str
    score: float
    rule_version: str
    market_cap: float = 0.0


@dataclass(frozen=True)
class PercentileExclusion:
    """One name excluded by the bottom-percentile gate."""

    ticker: str
    cik: str
    model: str
    score: float
    rule_id: str
    rule_version: str
    threshold_percentile: float
    explanation: str


def apply_bottom_percentile_gate(
    scores: list[ForensicScore],
    *,
    config: dict | None = None,
) -> list[PercentileExclusion]:
    """Hard-exclude names in the bottom ``bottom_percentile`` by score (higher = worse)."""
    if not scores:
        return []

    cfg = config or load_forensic_gate_config()
    percentile = float(cfg["bottom_percentile"])
    rule_id = str(cfg["rule_id"])
    score_label = str(cfg.get("score_label", "score"))
    exclude_count = max(1, math.ceil(len(scores) * percentile))

    ordered = sorted(scores, key=lambda row: (-row.score, row.market_cap))
    excluded = ordered[:exclude_count]
    return [
        PercentileExclusion(
            ticker=row.ticker,
            cik=row.cik,
            model=row.model,
            score=row.score,
            rule_id=rule_id,
            rule_version=row.rule_version,
            threshold_percentile=percentile,
            explanation=f"{score_label}={row.score:.4f} in bottom {percentile:.0%}",
        )
        for row in excluded
    ]
