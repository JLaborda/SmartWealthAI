"""Prepare a hermetic ``pipeline.joblib`` for the bake-image serve demo (#173)."""

from __future__ import annotations

from pathlib import Path

from credit.application_mart import build_application_mart
from credit.scoring_pipeline import ARTIFACT_NAME, fit_scoring_pipeline

# Default relative to repo root when callers pass only output_dir via the script.
DEFAULT_SCORING_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "credit"
    / "fixtures"
    / "scoring_mart"
    / "applications.csv"
)


def prepare_serve_demo_artifact(
    output_dir: Path,
    *,
    source: Path | None = None,
) -> Path:
    """Fit a CSS pipeline into ``output_dir`` and return the joblib path.

    Uses the hermetic scoring fixture unless ``source`` is provided. Mart
    intermediates go under ``output_dir / "_mart"``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(source) if source is not None else DEFAULT_SCORING_FIXTURE

    mart = build_application_mart(
        source_path,
        output_dir / "_mart",
        application_id_column="customer_ID",
        target_column="target",
        bad_value=1,
        good_value=0,
    )
    fit_scoring_pipeline(
        mart.mart_path,
        output_dir,
        application_id_column="customer_ID",
        target_column="target",
        random_state=42,
        skip_mlflow=True,
    )
    artifact = output_dir / ARTIFACT_NAME
    if not artifact.is_file():
        raise FileNotFoundError(f"Expected artifact missing: {artifact}")
    return artifact
