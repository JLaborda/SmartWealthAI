"""Public-interface tests for chapter 5 scratch scoring (#145)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

FIXTURE_MART = Path(__file__).parent / "fixtures" / "scoring_mart" / "applications.csv"


def _build_mart(tmp_path: Path) -> Path:
    """Materialize the hermetic scoring fixture as an application mart parquet."""
    from credit.application_mart import build_application_mart

    out = tmp_path / "mart"
    result = build_application_mart(
        FIXTURE_MART,
        out,
        application_id_column="customer_ID",
        target_column="target",
        bad_value=1,
        good_value=0,
    )
    assert result.retained_rows >= 30
    return result.mart_path


def test_fit_exports_joblib_and_reports_holdout_auc_ks(tmp_path: Path) -> None:
    """Fit on develop only → pipeline.joblib + holdout AUC/KS (public seam)."""
    from credit.scoring_pipeline import ARTIFACT_NAME, fit_scoring_pipeline

    mart_path = _build_mart(tmp_path)
    artifact_dir = tmp_path / "artifact"
    result = fit_scoring_pipeline(
        mart_path,
        artifact_dir,
        application_id_column="customer_ID",
        target_column="target",
        random_state=42,
    )

    assert (artifact_dir / ARTIFACT_NAME).is_file()
    assert 0.5 <= result.holdout_auc <= 1.0
    assert 0.0 <= result.holdout_ks <= 1.0
    assert result.n_develop > 0
    assert result.n_holdout > 0
    assert result.n_develop + result.n_holdout == result.n_scored
    # Leakage guard: WOE/IV fitted without holdout rows in the develop partition.
    assert result.fit_partition == "develop"


def test_score_emits_pd_credit_score_and_rank(tmp_path: Path) -> None:
    """Score path loads joblib and emits PD, book-scaled credit score, and rank."""
    from credit.scoring_pipeline import ARTIFACT_NAME, fit_scoring_pipeline, score_applications

    mart_path = _build_mart(tmp_path)
    artifact_dir = tmp_path / "artifact"
    fit_scoring_pipeline(
        mart_path,
        artifact_dir,
        application_id_column="customer_ID",
        target_column="target",
        random_state=42,
    )

    scores_path = tmp_path / "scores.parquet"
    result = score_applications(
        artifact_dir / ARTIFACT_NAME,
        mart_path,
        scores_path,
    )
    assert scores_path.is_file()
    frame = pd.read_parquet(scores_path)
    for col in ("customer_ID", "pd", "credit_score", "rank"):
        assert col in frame.columns
    assert len(frame) == result.n_scored
    assert frame["rank"].min() == 1
    assert frame["rank"].max() == len(frame)
    # Book PDO: higher credit_score = safer; rank 1 = highest score.
    top = frame.loc[frame["rank"] == 1].iloc[0]
    assert top["credit_score"] == frame["credit_score"].max()
    assert frame["pd"].between(0.0, 1.0).all()
    assert frame["credit_score"].between(250.0, 1000.0).all()


def test_woe_iv_pair_keeps_stronger_of_p2_and_d48(tmp_path: Path) -> None:
    """EDA wrap: WOE both P_2_last and D_48_last; drop the weaker by develop IV."""
    from credit.scoring_pipeline import fit_scoring_pipeline, load_pipeline

    mart_path = _build_mart(tmp_path)
    artifact_dir = tmp_path / "artifact"
    fit_scoring_pipeline(
        mart_path,
        artifact_dir,
        application_id_column="customer_ID",
        target_column="target",
        random_state=42,
    )
    pipeline = load_pipeline(artifact_dir / "pipeline.joblib")
    features = set(pipeline.feature_names)
    assert "P_2_last" in features or "D_48_last" in features
    assert not ({"P_2_last", "D_48_last"} <= features)
    assert "B_38_last" in features
    assert "B_38_mode" not in features
    assert not any("x" in f.lower() or "interact" in f.lower() for f in features)


def test_cli_fit_and_score_print_metrics(tmp_path: Path) -> None:
    """credit-css fit / score are thin wrappers around the public pipeline seam."""
    from credit.cli import main

    mart_path = _build_mart(tmp_path)
    artifact_dir = tmp_path / "artifact"
    scores_path = tmp_path / "scores.parquet"
    runner = CliRunner()

    fit = runner.invoke(
        main,
        [
            "fit",
            "--mart",
            str(mart_path),
            "--output-dir",
            str(artifact_dir),
            "--application-id-column",
            "customer_ID",
            "--target-column",
            "target",
            "--random-state",
            "42",
            "--skip-mlflow",
        ],
    )
    assert fit.exit_code == 0, fit.output
    assert "pipeline.joblib" in fit.output
    assert "AUC" in fit.output.upper() or "auc" in fit.output
    assert "KS" in fit.output.upper() or "ks" in fit.output

    score = runner.invoke(
        main,
        [
            "score",
            "--artifact",
            str(artifact_dir / "pipeline.joblib"),
            "--mart",
            str(mart_path),
            "--output",
            str(scores_path),
        ],
    )
    assert score.exit_code == 0, score.output
    assert scores_path.is_file()


def test_null_drop_threshold_default_is_eighty_percent() -> None:
    """EDA wrap: keep the 80% null-drop shortlist rule as the public default."""
    from credit.feature_selection import NULL_DROP_THRESHOLD

    assert NULL_DROP_THRESHOLD == pytest.approx(0.80)


def test_fit_logs_mlflow_params_metrics_and_artifact(tmp_path: Path) -> None:
    """Fit logs params, holdout metrics, and joblib to a local MLflow file store."""
    from credit.scoring_pipeline import ARTIFACT_NAME, fit_scoring_pipeline

    mart_path = _build_mart(tmp_path)
    artifact_dir = tmp_path / "artifact"
    tracking = tmp_path / "mlruns"
    result = fit_scoring_pipeline(
        mart_path,
        artifact_dir,
        application_id_column="customer_ID",
        target_column="target",
        random_state=42,
        skip_mlflow=False,
        mlflow_tracking_uri=tracking.as_uri(),
    )
    assert result.mlflow_run_id
    assert (artifact_dir / ARTIFACT_NAME).is_file()
    # File store layout created under tracking dir.
    assert tracking.exists()
    assert any(tracking.rglob("pipeline.joblib"))
