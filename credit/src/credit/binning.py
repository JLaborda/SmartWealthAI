"""Manual WOE / IV binning fitted on develop only (#145).

Clear module boundary so OptBinning / logistic scorecards can swap later
without rewriting CLI / Docker.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_EPS = 1e-6
_MAX_CAT_CARDINALITY = 12


@dataclass
class FeatureBins:
    """Fitted WOE map for one feature."""

    feature: str
    kind: str  # "numeric" | "categorical"
    iv: float
    # numeric: right edges for np.digitize (len = n_bins); woe[i] for bin i
    edges: tuple[float, ...] | None = None
    woe_by_bin: tuple[float, ...] | None = None
    # categorical: level → woe
    woe_by_level: dict[str, float] | None = None
    default_woe: float = 0.0


@dataclass
class WoeBinner:
    """Fit WOE encodings on develop; transform any frame with the same schema."""

    n_bins: int = 5
    feature_bins: dict[str, FeatureBins] = field(default_factory=dict)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> WoeBinner:
        y = pd.Series(y).astype(int).reset_index(drop=True)
        X = X.reset_index(drop=True)
        self.feature_bins = {}
        for col in X.columns:
            series = X[col]
            if _treat_as_categorical(series):
                self.feature_bins[col] = _fit_categorical(col, series, y)
            else:
                self.feature_bins[col] = _fit_numeric(col, series, y, n_bins=self.n_bins)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.feature_bins:
            raise RuntimeError("WoeBinner.fit must be called before transform")
        out = pd.DataFrame(index=X.index)
        for col, fb in self.feature_bins.items():
            if col not in X.columns:
                raise KeyError(f"Missing feature for WOE transform: {col}")
            out[col] = _apply_bins(X[col], fb)
        return out

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        return self.fit(X, y).transform(X)

    @property
    def iv_by_feature(self) -> dict[str, float]:
        return {name: fb.iv for name, fb in self.feature_bins.items()}


def _treat_as_categorical(series: pd.Series) -> bool:
    nunique = int(series.nunique(dropna=True))
    if nunique == 0:
        return True
    if not pd.api.types.is_numeric_dtype(series):
        return True
    # Low-cardinality numeric codes (B_38_last, B_30_last, …).
    return nunique <= _MAX_CAT_CARDINALITY


def _fit_numeric(name: str, series: pd.Series, y: pd.Series, *, n_bins: int) -> FeatureBins:
    values = series.astype(float)
    valid_mask = values.notna()
    valid = values[valid_mask]
    if valid.empty or valid.nunique() < 2:
        return FeatureBins(
            feature=name,
            kind="numeric",
            iv=0.0,
            edges=(),
            woe_by_bin=(0.0,),
            default_woe=0.0,
        )

    qs = np.linspace(0, 1, max(n_bins, 2) + 1)[1:-1]
    inner = np.unique(np.quantile(valid.to_numpy(), qs))
    edges = tuple(float(e) for e in inner)
    # digitize: bin 0 → (−inf, e0], …, bin len(edges) → (e_last, +inf)
    n_out_bins = len(edges) + 1
    bin_ids = np.full(len(values), -1, dtype=int)
    bin_ids[valid_mask.to_numpy()] = np.digitize(
        values[valid_mask].to_numpy(), bins=np.asarray(edges), right=True
    )

    woes, iv = _woe_for_bin_ids(bin_ids, y.to_numpy(), n_bins=n_out_bins)
    return FeatureBins(
        feature=name,
        kind="numeric",
        iv=iv,
        edges=edges,
        woe_by_bin=tuple(woes),
        default_woe=0.0,
    )


def _fit_categorical(name: str, series: pd.Series, y: pd.Series) -> FeatureBins:
    levels = series.fillna("__MISSING__").astype(str)
    y_arr = y.to_numpy()
    total_bad = float(y_arr.sum())
    total_good = float(len(y_arr) - y_arr.sum())
    woe_by_level: dict[str, float] = {}
    iv = 0.0
    if total_bad <= 0 or total_good <= 0:
        return FeatureBins(
            feature=name,
            kind="categorical",
            iv=0.0,
            woe_by_level={},
            default_woe=0.0,
        )

    for level, idx in levels.groupby(levels).groups.items():
        mask = y_arr[np.asarray(idx)]
        bad = float(mask.sum())
        good = float(len(mask) - bad)
        dist_bad = (bad + _EPS) / (total_bad + _EPS)
        dist_good = (good + _EPS) / (total_good + _EPS)
        woe = float(np.log(dist_good / dist_bad))
        iv += (dist_good - dist_bad) * woe
        woe_by_level[str(level)] = woe

    return FeatureBins(
        feature=name,
        kind="categorical",
        iv=float(iv),
        woe_by_level=woe_by_level,
        default_woe=0.0,
    )


def _woe_for_bin_ids(
    bin_ids: np.ndarray,
    y: np.ndarray,
    *,
    n_bins: int,
) -> tuple[list[float], float]:
    total_bad = float(y.sum())
    total_good = float(len(y) - y.sum())
    woes = [0.0] * n_bins
    iv = 0.0
    if total_bad <= 0 or total_good <= 0:
        return woes, 0.0

    for b in range(n_bins):
        mask = bin_ids == b
        if not np.any(mask):
            continue
        bad = float(y[mask].sum())
        good = float(mask.sum() - bad)
        dist_bad = (bad + _EPS) / (total_bad + _EPS)
        dist_good = (good + _EPS) / (total_good + _EPS)
        woe = float(np.log(dist_good / dist_bad))
        woes[b] = woe
        iv += (dist_good - dist_bad) * woe
    return woes, float(iv)


def _apply_bins(series: pd.Series, fb: FeatureBins) -> pd.Series:
    if fb.kind == "categorical":
        levels = series.fillna("__MISSING__").astype(str)
        mapping = fb.woe_by_level or {}
        return levels.map(lambda v: mapping.get(v, fb.default_woe)).astype(float)

    values = series.astype(float)
    out = np.full(len(values), fb.default_woe, dtype=float)
    valid = values.notna().to_numpy()
    edges = fb.edges or ()
    woes = fb.woe_by_bin or (fb.default_woe,)
    if not valid.any():
        return pd.Series(out, index=series.index)
    if not edges:
        out[valid] = woes[0]
        return pd.Series(out, index=series.index)
    ids = np.digitize(values[valid].to_numpy(), bins=np.asarray(edges), right=True)
    # Guard against unexpected length drift.
    mapped = [woes[i] if 0 <= i < len(woes) else fb.default_woe for i in ids]
    out[valid] = mapped
    return pd.Series(out, index=series.index)
