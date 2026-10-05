"""FastAPI serving for CSS scratch scoring (Friday demo week).

Loads the same ``pipeline.joblib`` as ``credit-css score`` / batch Docker.
Request body is feature JSON (example payloads from the hermetic scoring fixture).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from credit.model import predict_pd
from credit.score_scaling import pd_to_credit_score
from credit.scoring_pipeline import CreditScorePipeline, load_pipeline

ARTIFACT_ENV = "CREDIT_PIPELINE_ARTIFACT"
DEFAULT_TOP_K = 5


class ScoreRequest(BaseModel):
    application_id: str
    features: dict[str, Any]


class ScoreResponse(BaseModel):
    application_id: str
    pd: float
    credit_score: float
    rank: int


class DriversRequest(BaseModel):
    application_id: str
    features: dict[str, Any]
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1)


class DriverItem(BaseModel):
    feature: str
    score: float
    gain: float
    abs_woe: float


class DriversResponse(BaseModel):
    application_id: str
    method: str
    drivers: list[DriverItem]


def create_app(*, artifact_path: Path | str | None = None) -> FastAPI:
    """Build the CSS scoring API. Artifact path from arg or ``CREDIT_PIPELINE_ARTIFACT``."""
    path = Path(artifact_path or os.environ.get(ARTIFACT_ENV, ""))
    if not path.is_file():
        raise FileNotFoundError(
            f"pipeline artifact not found: {path!s} "
            f"(set {ARTIFACT_ENV} or pass artifact_path=)"
        )
    pipeline = load_pipeline(path)

    app = FastAPI(
        title="SmartWealthAI Credit CSS",
        description="Application credit scoring — PD, credit score, risk drivers.",
        version="0.1.0",
    )
    app.state.pipeline = pipeline

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/score", response_model=ScoreResponse)
    def score(body: ScoreRequest) -> ScoreResponse:
        try:
            result = score_features(pipeline, body.features)
        except KeyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return ScoreResponse(
            application_id=body.application_id,
            pd=result["pd"],
            credit_score=result["credit_score"],
            rank=1,  # single-application request
        )

    @app.post("/drivers", response_model=DriversResponse)
    def drivers(body: DriversRequest) -> DriversResponse:
        try:
            items = risk_drivers(pipeline, body.features, top_k=body.top_k)
        except KeyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return DriversResponse(
            application_id=body.application_id,
            method="gain_x_abs_woe",
            drivers=[DriverItem(**item) for item in items],
        )

    return app


def score_features(
    pipeline: CreditScorePipeline,
    features: dict[str, Any],
) -> dict[str, float]:
    """Score one applicant feature map → pd + credit_score."""
    frame = _features_frame(pipeline, features)
    X = pipeline.binner.transform(frame[pipeline.feature_names])
    pd_hat = float(predict_pd(pipeline.model, X)[0])
    credit_score = float(pd_to_credit_score([pd_hat], pipeline.scaling)[0])
    return {"pd": pd_hat, "credit_score": credit_score}


def risk_drivers(
    pipeline: CreditScorePipeline,
    features: dict[str, Any],
    *,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, float | str]]:
    """Top-k risk drivers for one row: gain × |WOE| (SHAP deferred)."""
    frame = _features_frame(pipeline, features)
    X = pipeline.binner.transform(frame[pipeline.feature_names])
    woe_row = X.iloc[0]
    gains = _feature_gains(pipeline)
    ranked: list[dict[str, float | str]] = []
    for name in pipeline.feature_names:
        gain = float(gains.get(name, 0.0))
        abs_woe = abs(float(woe_row[name]))
        ranked.append(
            {
                "feature": name,
                "gain": gain,
                "abs_woe": abs_woe,
                "score": gain * abs_woe,
            }
        )
    ranked.sort(key=lambda item: float(item["score"]), reverse=True)
    return ranked[: min(top_k, len(ranked))]


def _feature_gains(pipeline: CreditScorePipeline) -> dict[str, float]:
    """XGBoost gain per feature name (0.0 when unused by trees)."""
    model = pipeline.model
    names = list(pipeline.feature_names)
    # Prefer booster gain map keyed by feature name (xgboost 2.x + DataFrame fit).
    booster = getattr(model, "get_booster", lambda: None)()
    if booster is not None:
        raw = booster.get_score(importance_type="gain")
        if raw:
            # Keys may be feature names or f0/f1 when fitted without names.
            if all(k in names for k in raw):
                return {k: float(v) for k, v in raw.items()}
            mapped: dict[str, float] = {}
            for key, value in raw.items():
                if key.startswith("f") and key[1:].isdigit():
                    idx = int(key[1:])
                    if 0 <= idx < len(names):
                        mapped[names[idx]] = float(value)
                elif key in names:
                    mapped[key] = float(value)
            if mapped:
                return mapped
    importances = getattr(model, "feature_importances_", None)
    if importances is not None and len(importances) == len(names):
        return {name: float(imp) for name, imp in zip(names, importances, strict=True)}
    return {name: 0.0 for name in names}


def _features_frame(
    pipeline: CreditScorePipeline,
    features: dict[str, Any],
) -> pd.DataFrame:
    missing = [c for c in pipeline.feature_names if c not in features]
    if missing:
        raise KeyError(f"Missing required features: {missing}")
    row = {name: features[name] for name in pipeline.feature_names}
    return pd.DataFrame([row])


def main() -> None:
    """CLI entry: ``uvicorn`` factory against ``CREDIT_PIPELINE_ARTIFACT``."""
    import uvicorn

    uvicorn.run(
        "credit.api:create_app",
        factory=True,
        host=os.environ.get("CREDIT_API_HOST", "0.0.0.0"),
        port=int(os.environ.get("CREDIT_API_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
