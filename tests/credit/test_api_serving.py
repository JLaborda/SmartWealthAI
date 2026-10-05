"""Hermetic FastAPI serving tests — score + risk drivers (Friday demo week)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE_MART = Path(__file__).parent / "fixtures" / "scoring_mart" / "applications.csv"
EXAMPLE_PAYLOAD = Path(__file__).parent / "fixtures" / "serving" / "score_request.json"
DRIVERS_PAYLOAD = Path(__file__).parent / "fixtures" / "serving" / "drivers_request.json"


def _fit_artifact(tmp_path: Path) -> Path:
    from credit.application_mart import build_application_mart
    from credit.scoring_pipeline import ARTIFACT_NAME, fit_scoring_pipeline

    mart_out = tmp_path / "mart"
    mart = build_application_mart(
        FIXTURE_MART,
        mart_out,
        application_id_column="customer_ID",
        target_column="target",
        bad_value=1,
        good_value=0,
    )
    artifact_dir = tmp_path / "artifact"
    fit_scoring_pipeline(
        mart.mart_path,
        artifact_dir,
        application_id_column="customer_ID",
        target_column="target",
        random_state=42,
        skip_mlflow=True,
    )
    path = artifact_dir / ARTIFACT_NAME
    assert path.is_file()
    return path


def _client(artifact: Path) -> TestClient:
    from credit.api import create_app

    return TestClient(create_app(artifact_path=artifact))


def test_post_score_returns_pd_credit_score_and_rank(tmp_path: Path) -> None:
    """POST /score with fixture feature JSON → pd, credit_score, rank."""
    import json

    artifact = _fit_artifact(tmp_path)
    body = json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))
    client = _client(artifact)

    response = client.post("/score", json=body)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["application_id"] == body["application_id"]
    assert 0.0 <= payload["pd"] <= 1.0
    assert 250.0 <= payload["credit_score"] <= 1000.0
    assert payload["rank"] == 1


def test_post_drivers_returns_top_k_gain_x_abs_woe(tmp_path: Path) -> None:
    """POST /drivers → top-k risk drivers ranked by gain × |WOE| (no SHAP)."""
    import json

    artifact = _fit_artifact(tmp_path)
    body = json.loads(DRIVERS_PAYLOAD.read_text(encoding="utf-8"))
    client = _client(artifact)

    response = client.post("/drivers", json=body)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["application_id"] == body["application_id"]
    assert payload["method"] == "gain_x_abs_woe"
    drivers = payload["drivers"]
    assert len(drivers) == body["top_k"]
    scores = [d["score"] for d in drivers]
    assert scores == sorted(scores, reverse=True)
    for driver in drivers:
        assert "feature" in driver
        assert driver["feature"] in body["features"]
        assert driver["gain"] >= 0.0
        assert driver["abs_woe"] >= 0.0
        assert driver["score"] == pytest.approx(driver["gain"] * driver["abs_woe"])


def test_create_app_requires_pipeline_joblib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing CREDIT_PIPELINE_ARTIFACT / path fails clearly before serving."""
    from credit.api import ARTIFACT_ENV, create_app, resolve_artifact_path

    monkeypatch.delenv(ARTIFACT_ENV, raising=False)
    with pytest.raises(FileNotFoundError, match=ARTIFACT_ENV):
        resolve_artifact_path()
    with pytest.raises(FileNotFoundError, match=ARTIFACT_ENV):
        create_app()

    missing = tmp_path / "nope" / "pipeline.joblib"
    monkeypatch.setenv(ARTIFACT_ENV, str(missing))
    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_artifact_path()


def test_create_app_loads_artifact_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """create_app() without artifact_path= loads CREDIT_PIPELINE_ARTIFACT from fit."""
    import json

    from credit.api import ARTIFACT_ENV, create_app

    artifact = _fit_artifact(tmp_path)
    monkeypatch.setenv(ARTIFACT_ENV, str(artifact))
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "pipeline.joblib" in health.json()["artifact"]

    body = json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))
    scored = client.post("/score", json=body)
    assert scored.status_code == 200
    assert scored.json()["rank"] == 1
