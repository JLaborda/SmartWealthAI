"""Probability → credit score scaling (book-style pdo / base params).

Interim defaults follow common textbook Siddiqi-style values used across CSS
demos (PDO=20, base score=600 at odds 50:1). Exact chapter-5 notebook triples
were not recovered in-repo — see open question in the #145 handoff / PR.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

# Interim — not recovered from the book notebook; documented for Jorge review.
DEFAULT_PDO = 20.0
DEFAULT_BASE_SCORE = 600.0
DEFAULT_BASE_ODDS = 50.0  # good:bad at base_score


@dataclass(frozen=True)
class ScoreScalingParams:
    """pdo / base score / base odds for PD → credit score points."""

    pdo: float = DEFAULT_PDO
    base_score: float = DEFAULT_BASE_SCORE
    base_odds: float = DEFAULT_BASE_ODDS

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, float]) -> ScoreScalingParams:
        return cls(
            pdo=float(raw["pdo"]),
            base_score=float(raw["base_score"]),
            base_odds=float(raw["base_odds"]),
        )


def pd_to_credit_score(
    pd: np.ndarray,
    params: ScoreScalingParams | None = None,
) -> np.ndarray:
    """Map default probability to credit score points (higher = safer).

    score = Offset + Factor * ln((1 − PD) / PD)
    Factor = PDO / ln(2)
    Offset = base_score − Factor * ln(base_odds)
    """
    params = params or ScoreScalingParams()
    pd_arr = np.clip(np.asarray(pd, dtype=float), 1e-6, 1.0 - 1e-6)
    factor = params.pdo / np.log(2.0)
    offset = params.base_score - factor * np.log(params.base_odds)
    odds_good = (1.0 - pd_arr) / pd_arr
    return offset + factor * np.log(odds_good)
