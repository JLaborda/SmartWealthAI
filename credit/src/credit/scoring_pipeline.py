"""Fit / score orchestration + joblib artifact contract (#145).

Public seam for CLI and Docker batch score. Binning and model stay behind
``credit.binning`` / ``credit.model`` so they can be swapped later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from credit.binning import WoeBinner
from credit.feature_selection import (
    IV_PAIR_CANDIDATES,
    select_scorecard_features,
)
from credit.metrics import auc_roc, ks_statistic
from credit.model import build_xgb_classifier, fit_classifier, predict_pd
from credit.score_scaling import ScoreScalingParams, pd_to_credit_score

ARTIFACT_NAME = "pipeline.joblib"
DEFAULT_HOLDOUT_FRACTION = 0.3


@dataclass
class CreditScorePipeline:
    """Serializable scoring artifact: WOE binner + model + scaling params."""

    binner: WoeBinner
    model: Any
    scaling: ScoreScalingParams
    feature_names: list[str]
    application_id_column: str
    target_column: str
    wrap_notes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FitResult:
    artifact_path: Path
    holdout_auc: float
    holdout_ks: float
    develop_auc: float
    develop_ks: float
    n_develop: int
    n_holdout: int
    n_scored: int
    fit_partition: str
    feature_names: list[str]
    mlflow_run_id: str | None = None


@dataclass(frozen=True)
class ScoreResult:
    scores_path: Path
    n_scored: int


def fit_scoring_pipeline(
    mart_path: Path,
    output_dir: Path,
    *,
    application_id_column: str = "customer_ID",
    target_column: str = "target",
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    random_state: int = 42,
    scaling: ScoreScalingParams | None = None,
    skip_mlflow: bool = False,
    mlflow_tracking_uri: str | None = None,
) -> FitResult:
    """Develop-only WOE/IV + XGBoost → ``pipeline.joblib`` + holdout AUC/KS."""
    mart_path = Path(mart_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scaling = scaling or ScoreScalingParams()

    frame = _load_mart(mart_path)
    _require_columns(frame, application_id_column, target_column)

    y = frame[target_column].astype(int)
    develop_idx, holdout_idx = train_test_split(
        frame.index,
        test_size=holdout_fraction,
        random_state=random_state,
        stratify=y,
    )
    develop = frame.loc[develop_idx].reset_index(drop=True)
    holdout = frame.loc[holdout_idx].reset_index(drop=True)

    # Pass 1: provisional shortlist (both P_2 and D_48 if present) → IV on develop.
    provisional = select_scorecard_features(
        develop,
        iv_by_feature=None,
        application_id_column=application_id_column,
        target_column=target_column,
    )
    provisional = [c for c in provisional if c in develop.columns]
    if not provisional:
        raise ValueError("No candidate features left after null-drop / shortlist")

    probe = WoeBinner()
    probe.fit(develop[provisional], develop[target_column])
    iv_map = probe.iv_by_feature

    # Pass 2: drop weaker of P_2_last / D_48_last by develop IV.
    final_features = select_scorecard_features(
        develop,
        iv_by_feature=iv_map,
        application_id_column=application_id_column,
        target_column=target_column,
    )
    final_features = [c for c in final_features if c in develop.columns]
    # Ensure we never keep both IV-pair candidates.
    pair_kept = [c for c in IV_PAIR_CANDIDATES if c in final_features]
    if len(pair_kept) > 1:
        stronger = max(pair_kept, key=lambda c: iv_map.get(c, 0.0))
        final_features = [c for c in final_features if c not in IV_PAIR_CANDIDATES]
        final_features.insert(0, stronger)

    binner = WoeBinner()
    X_dev = binner.fit_transform(develop[final_features], develop[target_column])
    y_dev = develop[target_column].astype(int)

    model = build_xgb_classifier(random_state=random_state)
    fit_classifier(model, X_dev, y_dev)

    X_hold = binner.transform(holdout[final_features])
    y_hold = holdout[target_column].astype(int)
    pd_dev = predict_pd(model, X_dev)
    pd_hold = predict_pd(model, X_hold)

    develop_auc = auc_roc(y_dev.to_numpy(), pd_dev)
    develop_ks = ks_statistic(y_dev.to_numpy(), pd_dev)
    holdout_auc = auc_roc(y_hold.to_numpy(), pd_hold)
    holdout_ks = ks_statistic(y_hold.to_numpy(), pd_hold)

    pipeline = CreditScorePipeline(
        binner=binner,
        model=model,
        scaling=scaling,
        feature_names=list(final_features),
        application_id_column=application_id_column,
        target_column=target_column,
        wrap_notes={
            "null_drop_threshold": 0.80,
            "preferred_b38": "B_38_last",
            "iv_pair": list(IV_PAIR_CANDIDATES),
            "kept_iv_pair_member": next(
                (c for c in IV_PAIR_CANDIDATES if c in final_features), None
            ),
            "include_b38_b30_interaction": False,
            "iv_by_feature": {k: float(v) for k, v in binner.iv_by_feature.items()},
        },
    )
    artifact_path = output_dir / ARTIFACT_NAME
    joblib.dump(pipeline, artifact_path)

    mlflow_run_id = None
    if not skip_mlflow:
        from credit.mlflow_logging import log_fit_run

        mlflow_run_id = log_fit_run(
            artifact_path=artifact_path,
            params={
                "application_id_column": application_id_column,
                "target_column": target_column,
                "holdout_fraction": holdout_fraction,
                "random_state": random_state,
                "n_features": len(final_features),
                "features": ",".join(final_features),
                "pdo": scaling.pdo,
                "base_score": scaling.base_score,
                "base_odds": scaling.base_odds,
                "scaling_source": "book_chapter5_pdo_good_odds",
            },
            metrics={
                "develop_auc": develop_auc,
                "develop_ks": develop_ks,
                "holdout_auc": holdout_auc,
                "holdout_ks": holdout_ks,
                "n_develop": float(len(develop)),
                "n_holdout": float(len(holdout)),
            },
            tracking_uri=mlflow_tracking_uri,
        )

    return FitResult(
        artifact_path=artifact_path,
        holdout_auc=holdout_auc,
        holdout_ks=holdout_ks,
        develop_auc=develop_auc,
        develop_ks=develop_ks,
        n_develop=len(develop),
        n_holdout=len(holdout),
        n_scored=len(develop) + len(holdout),
        fit_partition="develop",
        feature_names=list(final_features),
        mlflow_run_id=mlflow_run_id,
    )


def load_pipeline(artifact_path: Path) -> CreditScorePipeline:
    pipeline = joblib.load(Path(artifact_path))
    if not isinstance(pipeline, CreditScorePipeline):
        raise TypeError(f"Unexpected artifact type: {type(pipeline)!r}")
    return pipeline


def score_applications(
    artifact_path: Path,
    mart_path: Path,
    output_path: Path,
) -> ScoreResult:
    """Load ``pipeline.joblib`` → PD + book credit score + rank (1 = safest)."""
    pipeline = load_pipeline(artifact_path)
    frame = _load_mart(mart_path)
    _require_columns(frame, pipeline.application_id_column, *pipeline.feature_names)

    X = pipeline.binner.transform(frame[pipeline.feature_names])
    pd_hat = predict_pd(pipeline.model, X)
    scores = pd_to_credit_score(pd_hat, pipeline.scaling)

    out = pd.DataFrame(
        {
            pipeline.application_id_column: frame[pipeline.application_id_column].to_numpy(),
            "pd": pd_hat,
            "credit_score": scores,
        }
    )
    # Book PDO: higher credit_score = safer (good-borrower odds). Rank 1 = highest score.
    out["rank"] = out["credit_score"].rank(method="first", ascending=False).astype(int)
    out = out.sort_values("rank").reset_index(drop=True)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)
    return ScoreResult(scores_path=output_path, n_scored=len(out))


def _load_mart(path: Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    raise ValueError(f"Unsupported mart format: {path}")


def _require_columns(frame: pd.DataFrame, *columns: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise KeyError(f"Mart missing required columns: {missing}")
