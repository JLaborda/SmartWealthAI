"""Local PSI data-drift check for CSS v1 (Friday MUST).

Reference quantile bins (not WOE); Markdown + JSON report artifacts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from credit.model import predict_pd
from credit.score_scaling import pd_to_credit_score
from credit.scoring_pipeline import (
    DEFAULT_HOLDOUT_FRACTION,
    CreditScorePipeline,
    _load_mart,
    _require_columns,
    load_pipeline,
)

DEFAULT_PSI_STABLE = 0.10
DEFAULT_PSI_SEVERE = 0.25
N_PSI_BINS = 10
TOP_IV_FEATURES = 10
SYNTHETIC_DRIFT_SEED = 42
PSI_EPSILON = 1e-4
N_SYNTHETIC_SHIFT_FEATURES = 2

_LABEL_RANK = {"stable": 0, "shift": 1, "severe": 2}


@dataclass(frozen=True)
class PsiColumnResult:
    column: str
    psi: float
    label: str


@dataclass(frozen=True)
class PsiReport:
    columns: list[PsiColumnResult]
    overall_label: str
    reference_n: int
    recent_n: int
    stable_threshold: float
    severe_threshold: float
    synthetic_drift: bool
    shifted_features: list[str] = field(default_factory=list)
    monitored_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_label": self.overall_label,
            "reference_n": self.reference_n,
            "recent_n": self.recent_n,
            "stable_threshold": self.stable_threshold,
            "severe_threshold": self.severe_threshold,
            "synthetic_drift": self.synthetic_drift,
            "shifted_features": list(self.shifted_features),
            "monitored_columns": list(self.monitored_columns),
            "columns": [asdict(c) for c in self.columns],
        }


def classify_psi(
    psi: float,
    *,
    stable_threshold: float = DEFAULT_PSI_STABLE,
    severe_threshold: float = DEFAULT_PSI_SEVERE,
) -> str:
    """Map PSI to stable / shift / severe using exclusive upper bound for stable."""
    if psi < stable_threshold:
        return "stable"
    if psi < severe_threshold:
        return "shift"
    return "severe"


def compute_psi(
    reference: pd.Series,
    recent: pd.Series,
    *,
    n_bins: int = N_PSI_BINS,
) -> float:
    """PSI with ``n_bins`` quantile edges from reference; same edges on recent."""
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    rec = pd.to_numeric(recent, errors="coerce").dropna()
    if ref.empty or rec.empty:
        return float("nan")

    # Quantile edges from reference only (not WOE bins).
    try:
        _, edges = pd.qcut(ref, q=n_bins, retbins=True, duplicates="drop")
    except ValueError:
        # Degenerate column (all equal) — single bin → PSI 0 if recent also constant.
        return 0.0 if rec.nunique(dropna=True) <= 1 else float("inf")

    edges = np.asarray(edges, dtype=float)
    # Open outer edges so min/max of recent always land in a bin.
    edges[0] = -np.inf
    edges[-1] = np.inf

    ref_counts = pd.cut(ref, bins=edges, include_lowest=True).value_counts(sort=False)
    rec_counts = pd.cut(rec, bins=edges, include_lowest=True).value_counts(sort=False)
    e = (ref_counts / ref_counts.sum()).to_numpy(dtype=float)
    a = (rec_counts / rec_counts.sum()).to_numpy(dtype=float)
    e = np.clip(e, PSI_EPSILON, None)
    a = np.clip(a, PSI_EPSILON, None)
    e = e / e.sum()
    a = a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))


def top_iv_features(pipeline: CreditScorePipeline, *, limit: int = TOP_IV_FEATURES) -> list[str]:
    """Top features by IV from the fitted artifact (descending)."""
    iv_map = pipeline.wrap_notes.get("iv_by_feature") or {}
    if iv_map:
        names = sorted(iv_map, key=lambda n: (-float(iv_map[n]), n))
    else:
        names = list(pipeline.feature_names)
    return names[:limit]


def apply_synthetic_drift(
    frame: pd.DataFrame,
    feature_names: list[str],
    *,
    seed: int = SYNTHETIC_DRIFT_SEED,
    n_shift: int = N_SYNTHETIC_SHIFT_FEATURES,
) -> tuple[pd.DataFrame, list[str]]:
    """Copy frame; shift/scale up to ``n_shift`` features so PSI goes red."""
    out = frame.copy()
    targets = list(feature_names[:n_shift])
    rng = np.random.default_rng(seed)
    for name in targets:
        if name not in out.columns:
            continue
        col = pd.to_numeric(out[name], errors="coerce")
        std = float(col.std(ddof=0))
        if not np.isfinite(std) or std == 0.0:
            std = 1.0
        # Large location + scale shock — fixed recipe for demo reproducibility.
        noise = rng.normal(loc=3.0 * std, scale=0.5 * std, size=len(out))
        out[name] = col * 2.5 + noise
    return out, targets


def _score_frame(pipeline: CreditScorePipeline, frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, *pipeline.feature_names)
    X = pipeline.binner.transform(frame[pipeline.feature_names])
    pd_hat = predict_pd(pipeline.model, X)
    scores = pd_to_credit_score(pd_hat, pipeline.scaling)
    scored = frame.copy()
    scored["pd"] = pd_hat
    scored["credit_score"] = scores
    return scored


def _split_develop_holdout(
    frame: pd.DataFrame,
    *,
    target_column: str,
    holdout_fraction: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Must match credit.scoring_pipeline.fit_scoring_pipeline split.
    y = frame[target_column].astype(int)
    develop_idx, holdout_idx = train_test_split(
        frame.index,
        test_size=holdout_fraction,
        random_state=random_state,
        stratify=y,
    )
    develop = frame.loc[develop_idx].reset_index(drop=True)
    holdout = frame.loc[holdout_idx].reset_index(drop=True)
    return develop, holdout


def _worst_label(labels: list[str]) -> str:
    return max(labels, key=lambda lab: _LABEL_RANK.get(lab, 0)) if labels else "stable"


def _write_reports(report: PsiReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (output_dir / "psi_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# PSI data-drift report",
        "",
        f"- **Overall:** `{report.overall_label}`",
        f"- **Reference n:** {report.reference_n}",
        f"- **Recent n:** {report.recent_n}",
        f"- **Thresholds:** stable < {report.stable_threshold}, "
        f"shift < {report.severe_threshold}, severe >= {report.severe_threshold}",
        f"- **Synthetic drift:** {report.synthetic_drift}",
    ]
    if report.shifted_features:
        lines.append(f"- **Shifted features:** {', '.join(report.shifted_features)}")
    lines.extend(["", "| Column | PSI | Label |", "| --- | ---: | --- |"])
    for col in report.columns:
        lines.append(f"| `{col.column}` | {col.psi:.6f} | {col.label} |")
    lines.append("")
    (output_dir / "psi_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_psi_check(
    *,
    artifact_path: Path,
    output_dir: Path,
    mart_path: Path | None = None,
    reference_path: Path | None = None,
    recent_path: Path | None = None,
    synthetic_drift: bool = False,
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    random_state: int = 42,
    stable_threshold: float = DEFAULT_PSI_STABLE,
    severe_threshold: float = DEFAULT_PSI_SEVERE,
    include_pd: bool = True,
    n_bins: int = N_PSI_BINS,
) -> PsiReport:
    """Compare reference vs recent; write ``psi_report.md`` + ``psi_report.json``."""
    if severe_threshold <= stable_threshold:
        raise ValueError("severe_threshold must be greater than stable_threshold")

    pipeline = load_pipeline(artifact_path)
    iv_features = top_iv_features(pipeline)

    if mart_path is not None:
        if reference_path is not None or recent_path is not None:
            raise ValueError("Use either --mart or --reference/--recent, not both")
        frame = _load_mart(mart_path)
        _require_columns(
            frame,
            pipeline.application_id_column,
            pipeline.target_column,
            *pipeline.feature_names,
        )
        reference_raw, recent_raw = _split_develop_holdout(
            frame,
            target_column=pipeline.target_column,
            holdout_fraction=holdout_fraction,
            random_state=random_state,
        )
    else:
        if reference_path is None or recent_path is None:
            raise ValueError("Provide --mart or both --reference and --recent")
        reference_raw = _load_mart(reference_path)
        recent_raw = _load_mart(recent_path)
        _require_columns(reference_raw, *pipeline.feature_names)
        _require_columns(recent_raw, *pipeline.feature_names)

    shifted: list[str] = []
    if synthetic_drift:
        recent_raw, shifted = apply_synthetic_drift(recent_raw, iv_features)

    reference = _score_frame(pipeline, reference_raw)
    recent = _score_frame(pipeline, recent_raw)

    monitored: list[str] = ["credit_score"]
    if include_pd:
        monitored.append("pd")
    monitored.extend(iv_features)

    columns: list[PsiColumnResult] = []
    for name in monitored:
        if name not in reference.columns or name not in recent.columns:
            continue
        psi = compute_psi(reference[name], recent[name], n_bins=n_bins)
        label = classify_psi(
            psi,
            stable_threshold=stable_threshold,
            severe_threshold=severe_threshold,
        )
        columns.append(PsiColumnResult(column=name, psi=psi, label=label))

    report = PsiReport(
        columns=columns,
        overall_label=_worst_label([c.label for c in columns]),
        reference_n=len(reference),
        recent_n=len(recent),
        stable_threshold=stable_threshold,
        severe_threshold=severe_threshold,
        synthetic_drift=synthetic_drift,
        shifted_features=shifted,
        monitored_columns=[c.column for c in columns],
    )
    _write_reports(report, Path(output_dir))
    return report
