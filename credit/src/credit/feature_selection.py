"""Null-drop + IV threshold selection for chapter 5 scratch scoring.

Book-aligned: after dropping high-null columns, keep features with IV ≥ 0.02
(see chapter 5 notebook ``iv_threshold=0.02``). No fixed 8-feature shortlist.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

NULL_DROP_THRESHOLD = 0.80
IV_THRESHOLD = 0.02  # book ch.5 calculate_woe_iv


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


def candidate_features(
    frame: pd.DataFrame,
    *,
    application_id_column: str,
    target_column: str,
    null_drop_threshold: float = NULL_DROP_THRESHOLD,
) -> list[str]:
    """Feature columns after null-drop (excludes id / target)."""
    protect = (application_id_column, target_column)
    kept = drop_high_null_columns(frame, threshold=null_drop_threshold, protect=protect)
    return [c for c in kept if c not in protect]


def select_by_iv(
    iv_by_feature: Mapping[str, float],
    *,
    threshold: float = IV_THRESHOLD,
) -> list[str]:
    """Keep features with IV ≥ threshold; stable order by IV descending then name."""
    kept = [name for name, iv in iv_by_feature.items() if float(iv) >= threshold]
    kept.sort(key=lambda name: (-float(iv_by_feature[name]), name))
    return kept
