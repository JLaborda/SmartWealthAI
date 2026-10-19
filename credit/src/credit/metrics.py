"""Holdout discrimination metrics for CSS scratch scoring (#145)."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score


def auc_roc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """AUC-ROC for ranking bad vs good (higher score = higher P(bad))."""
    return float(roc_auc_score(y_true, y_score))


def ks_statistic(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Kolmogorov–Smirnov statistic between score CDFs of bad and good.

    Uses predicted PD (higher = riskier). Returns max |F_bad − F_good|.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    order = np.argsort(y_score)
    y_sorted = y_true[order]
    n_bad = int(y_sorted.sum())
    n_good = int(len(y_sorted) - n_bad)
    if n_bad == 0 or n_good == 0:
        return 0.0
    cum_bad = np.cumsum(y_sorted) / n_bad
    cum_good = np.cumsum(1 - y_sorted) / n_good
    return float(np.max(np.abs(cum_bad - cum_good)))
