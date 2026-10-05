"""EDA wrap defaults and shortlist feature selection for #145.

Boundaries: selection only — no WOE bins and no model here (swap later).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

# Locked EDA wrap defaults (plan-145 / guided EDA).
NULL_DROP_THRESHOLD = 0.80
PREFERRED_B38 = "B_38_last"
IV_PAIR_CANDIDATES = ("P_2_last", "D_48_last")
INCLUDE_B38_B30_INTERACTION = False

# Secondary numerics / cats kept when present after null drop (fixture-friendly).
_EXTRA_CANDIDATES = (
    "B_30_last",
    "B_2_last",
    "R_1_std",
    "R_1_max",
    "B_18_last",
    "B_9_last",
)


def drop_high_null_columns(
    frame: pd.DataFrame,
    *,
    threshold: float = NULL_DROP_THRESHOLD,
    protect: Sequence[str] = (),
) -> list[str]:
    """Return columns to keep after dropping those with null fraction ≥ threshold."""
    protect_set = set(protect)
    kept: list[str] = []
    n = len(frame)
    if n == 0:
        return list(frame.columns)
    for col in frame.columns:
        if col in protect_set:
            kept.append(col)
            continue
        null_frac = float(frame[col].isna().mean())
        if null_frac < threshold:
            kept.append(col)
    return kept


def select_scorecard_features(
    frame: pd.DataFrame,
    *,
    iv_by_feature: dict[str, float] | None = None,
    application_id_column: str,
    target_column: str,
) -> list[str]:
    """Shortlist features per EDA wrap defaults.

    - Prefer ``B_38_last`` (not ``B_38_mode``).
    - Of ``P_2_last`` / ``D_48_last``, keep both until IV is known; if IV map is
      provided, keep only the stronger.
    - No ``B_38×B_30`` interaction column.
    - After null drop, add a few secondary candidates when present.
    """
    protect = (application_id_column, target_column)
    kept_cols = set(drop_high_null_columns(frame, protect=protect))

    selected: list[str] = []

    if PREFERRED_B38 in kept_cols:
        selected.append(PREFERRED_B38)
    elif "B_38_mode" in kept_cols:
        # Fallback only if last is absent after null drop.
        selected.append("B_38_mode")

    pair_present = [c for c in IV_PAIR_CANDIDATES if c in kept_cols]
    if len(pair_present) == 2 and iv_by_feature is not None:
        stronger = max(pair_present, key=lambda c: iv_by_feature.get(c, 0.0))
        selected.append(stronger)
    else:
        selected.extend(pair_present)

    for col in _EXTRA_CANDIDATES:
        if col in kept_cols and col not in selected:
            selected.append(col)

    # Any remaining numeric/object feature columns for tiny fixtures that lack
    # the AMEX shortlist names (still after null drop).
    if not selected:
        for col in frame.columns:
            if col in protect or col not in kept_cols:
                continue
            selected.append(col)

    assert not INCLUDE_B38_B30_INTERACTION  # locked wrap default
    return selected
