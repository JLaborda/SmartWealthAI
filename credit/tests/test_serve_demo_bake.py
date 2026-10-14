"""Seam A: prepare demo artifact → FastAPI score/drivers (bake path, no Docker)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from credit.scoring_pipeline import ARTIFACT_NAME

EXAMPLE_PAYLOAD = Path(__file__).parent / "fixtures" / "serving" / "score_request.json"
DRIVERS_PAYLOAD = Path(__file__).parent / "fixtures" / "serving" / "drivers_request.json"
SCORING_FIXTURE = Path(__file__).parent / "fixtures" / "scoring_mart" / "applications.csv"


def test_prepare_serve_demo_artifact_serves_score_and_drivers(tmp_path: Path) -> None:
    """Hermetic prepare → joblib under output_dir → /score and /drivers succeed."""
    from credit.api import create_app
    from credit.demo_serve_artifact import prepare_serve_demo_artifact

    artifact = prepare_serve_demo_artifact(
        tmp_path / "demo_artifact",
        source=SCORING_FIXTURE,
    )
    assert artifact == tmp_path / "demo_artifact" / ARTIFACT_NAME
    assert artifact.is_file()

    client = TestClient(create_app(artifact_path=artifact))
    score_body = json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))
    drivers_body = json.loads(DRIVERS_PAYLOAD.read_text(encoding="utf-8"))

    score = client.post("/score", json=score_body)
    assert score.status_code == 200, score.text
    score_payload = score.json()
    assert score_payload["application_id"] == score_body["application_id"]
    assert 0.0 <= score_payload["pd"] <= 1.0
    assert 250.0 <= score_payload["credit_score"] <= 1000.0

    drivers = client.post("/drivers", json=drivers_body)
    assert drivers.status_code == 200, drivers.text
    drivers_payload = drivers.json()
    assert drivers_payload["method"] == "gain_x_abs_woe"
    assert len(drivers_payload["drivers"]) == drivers_body["top_k"]


def test_prepare_uses_default_scoring_fixture_when_source_omitted(
    tmp_path: Path,
) -> None:
    """Operator script path: no ``source`` → DEFAULT_SCORING_FIXTURE."""
    from credit.demo_serve_artifact import (
        DEFAULT_SCORING_FIXTURE,
        prepare_serve_demo_artifact,
    )

    assert DEFAULT_SCORING_FIXTURE.is_file()
    artifact = prepare_serve_demo_artifact(tmp_path / "demo_default")
    assert artifact == tmp_path / "demo_default" / ARTIFACT_NAME
    assert artifact.is_file()


def test_prepare_raises_when_fit_skips_writing_joblib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail clearly if fit returns without ``pipeline.joblib``."""
    from credit import demo_serve_artifact as mod

    monkeypatch.setattr(
        mod,
        "fit_scoring_pipeline",
        lambda *a, **k: None,
    )
    with pytest.raises(FileNotFoundError, match="Expected artifact missing"):
        mod.prepare_serve_demo_artifact(tmp_path / "empty", source=SCORING_FIXTURE)
