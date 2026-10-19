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


def test_resolve_artifact_path_rejects_blank_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only CREDIT_PIPELINE_ARTIFACT is treated as unset."""
    from credit.api import ARTIFACT_ENV, resolve_artifact_path

    monkeypatch.setenv(ARTIFACT_ENV, "   ")
    with pytest.raises(FileNotFoundError, match="path not set"):
        resolve_artifact_path()


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
    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_artifact_path(missing)


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


def test_score_and_drivers_return_422_when_features_missing(tmp_path: Path) -> None:
    """Missing required feature keys → HTTP 422 from both endpoints."""
    artifact = _fit_artifact(tmp_path)
    client = _client(artifact)
    body = {"application_id": "c001", "features": {"P_2_last": 0.9}}

    score = client.post("/score", json=body)
    assert score.status_code == 422
    assert "Missing required features" in score.json()["detail"]

    drivers = client.post("/drivers", json={**body, "top_k": 2})
    assert drivers.status_code == 422
    assert "Missing required features" in drivers.json()["detail"]


def test_feature_gains_maps_f_index_keys_and_fallbacks() -> None:
    """_feature_gains covers f0-style booster keys and importances fallback."""
    from unittest.mock import MagicMock

    from credit.api import _feature_gains

    names = ["a", "b"]

    # Booster returns f0/f1 keys (fit without feature names).
    pipeline = MagicMock()
    pipeline.feature_names = names
    booster = MagicMock()
    booster.get_score.return_value = {"f0": 2.0, "f1": 1.0, "noise": 9.0}
    pipeline.model.get_booster.return_value = booster
    assert _feature_gains(pipeline) == {"a": 2.0, "b": 1.0}

    # Named key + out-of-range f-index when not all keys are feature names.
    booster.get_score.return_value = {"a": 3.0, "f99": 1.0}
    assert _feature_gains(pipeline) == {"a": 3.0}

    # Non-empty booster score but nothing mappable → fall through to importances.
    booster.get_score.return_value = {"noise": 1.0, "f99": 2.0}
    pipeline.model.feature_importances_ = [0.4, 0.6]
    assert _feature_gains(pipeline) == {"a": 0.4, "b": 0.6}

    # Empty booster score → feature_importances_.
    booster.get_score.return_value = {}
    pipeline.model.feature_importances_ = [0.25, 0.75]
    assert _feature_gains(pipeline) == {"a": 0.25, "b": 0.75}

    # No booster, no importances → zeros.
    pipeline.model.get_booster.return_value = None
    pipeline.model.feature_importances_ = None
    assert _feature_gains(pipeline) == {"a": 0.0, "b": 0.0}


def test_main_exits_when_artifact_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """credit-css-serve / main() exits 2 before uvicorn when artifact unset."""
    from credit.api import ARTIFACT_ENV, main

    monkeypatch.delenv(ARTIFACT_ENV, raising=False)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert ARTIFACT_ENV in capsys.readouterr().err


def test_main_starts_uvicorn_when_artifact_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() resolves the fit joblib then hands off to uvicorn.run."""
    from credit.api import ARTIFACT_ENV, main

    artifact = _fit_artifact(tmp_path)
    monkeypatch.setenv(ARTIFACT_ENV, str(artifact))
    monkeypatch.setenv("CREDIT_API_HOST", "127.0.0.1")
    monkeypatch.setenv("CREDIT_API_PORT", "8765")

    called: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        called["app"] = app
        called.update(kwargs)

    monkeypatch.setattr("uvicorn.run", fake_run)
    main()
    assert called["app"] == "credit.api:create_app"
    assert called["factory"] is True
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 8765
