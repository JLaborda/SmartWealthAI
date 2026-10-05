"""XGBoost classifier boundary for CSS scratch scoring (#145).

Swap target: logistic / OptBinning scorecard can replace this module later
without changing CLI / Docker / artifact load seam.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBClassifier


def build_xgb_classifier(*, random_state: int = 42) -> XGBClassifier:
    """Small, deterministic XGB for hermetic demos (real model, not a stub)."""
    return XGBClassifier(
        n_estimators=30,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="auc",
        random_state=random_state,
        n_jobs=1,
        verbosity=0,
    )


def fit_classifier(model: Any, X: pd.DataFrame, y: pd.Series) -> Any:
    model.fit(X, y.astype(int))
    return model


def predict_pd(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Predicted probability of bad (positive class)."""
    proba = model.predict_proba(X)
    # Class order: [0, 1] when both present; take positive column.
    classes = list(getattr(model, "classes_", [0, 1]))
    if 1 in classes:
        return np.asarray(proba[:, classes.index(1)], dtype=float)
    return np.asarray(proba[:, -1], dtype=float)
