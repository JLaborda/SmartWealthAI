"""Probability → credit score scaling (book chapter 5 notebook).

Matches *Financial AI in Practice* ch.5 Part1 cells that set::

    base_score = 650
    PDO = 20
    factor = PDO / ln(2)
    offset = base_score - factor * ln(20)
    odds = PD / (1 - PD)   # default odds
    score = clip(offset + factor * ln(odds), 250, 1000)

Under this convention, **higher credit_score ↔ higher PD** (riskier).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

# Book chapter 5 scratch CSS notebook (Part1).
DEFAULT_PDO = 20.0
DEFAULT_BASE_SCORE = 650.0
DEFAULT_BASE_ODDS = 20.0  # used in offset; book default-odds convention
SCORE_CLIP_MIN = 250.0
SCORE_CLIP_MAX = 1000.0
SCALING_SOURCE = "book_chapter5_notebook"


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
    """Map default probability to book credit score points (higher = riskier).

    score = clip(Offset + Factor * ln(PD / (1 − PD)), 250, 1000)
    Factor = PDO / ln(2)
    Offset = base_score − Factor * ln(base_odds)
    """
    params = params or ScoreScalingParams()
    # Tiny floor so ln(odds) is defined; still extreme enough to hit book clips.
    pd_arr = np.clip(np.asarray(pd, dtype=float), 1e-12, 1.0 - 1e-12)
    factor = params.pdo / np.log(2.0)
    offset = params.base_score - factor * np.log(params.base_odds)
    odds_default = pd_arr / (1.0 - pd_arr)
    raw = offset + factor * np.log(odds_default)
    return np.clip(raw, SCORE_CLIP_MIN, SCORE_CLIP_MAX)
