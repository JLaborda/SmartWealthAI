"""Public-interface tests for local PSI data-drift CLI (Friday MUST)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

# Larger hermetic mart so 10-bin develop-vs-holdout PSI stays honestly stable.
FIXTURE_MART = Path(__file__).parent / "fixtures" / "psi_mart" / "applications.csv"


def _build_mart_and_artifact(tmp_path: Path) -> tuple[Path, Path]:
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
    return mart.mart_path, artifact_dir / ARTIFACT_NAME


def test_stable_psi_labels_credit_score_and_features_stable(tmp_path: Path) -> None:
    """Develop vs holdout (same split as fit) → stable labels on monitored columns."""
    from credit.psi import run_psi_check

    mart_path, artifact_path = _build_mart_and_artifact(tmp_path)
    out = tmp_path / "psi_out"
    report = run_psi_check(
        mart_path=mart_path,
        artifact_path=artifact_path,
        output_dir=out,
        synthetic_drift=False,
        random_state=42,
    )

    assert (out / "psi_report.json").is_file()
    assert (out / "psi_report.md").is_file()
    assert report.columns
    names = {c.column for c in report.columns}
    assert "credit_score" in names
    assert "pd" in names
    # Same-split develop vs holdout should not go severe on every column.
    assert all(c.label == "stable" for c in report.columns)
    assert report.overall_label == "stable"
    assert report.synthetic_drift is False


def test_synthetic_drift_raises_psi_on_shifted_features(tmp_path: Path) -> None:
    """--synthetic-drift shifts top-IV features so PSI goes severe on those cols."""
    from credit.psi import run_psi_check

    mart_path, artifact_path = _build_mart_and_artifact(tmp_path)
    stable = run_psi_check(
        mart_path=mart_path,
        artifact_path=artifact_path,
        output_dir=tmp_path / "psi_stable",
        synthetic_drift=False,
        random_state=42,
    )
    drifted = run_psi_check(
        mart_path=mart_path,
        artifact_path=artifact_path,
        output_dir=tmp_path / "psi_drift",
        synthetic_drift=True,
        random_state=42,
    )

    assert drifted.synthetic_drift is True
    assert drifted.shifted_features
    stable_by_col = {c.column: c for c in stable.columns}
    for name in drifted.shifted_features:
        d = next(c for c in drifted.columns if c.column == name)
        s = stable_by_col[name]
        assert d.psi > s.psi
        assert d.label == "severe"
        assert d.psi >= 0.25


def test_cli_psi_writes_reports(tmp_path: Path) -> None:
    """credit-css psi is a thin wrapper that writes md + json reports."""
    from credit.cli import main

    mart_path, artifact_path = _build_mart_and_artifact(tmp_path)
    out = tmp_path / "cli_psi"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "psi",
            "--mart",
            str(mart_path),
            "--artifact",
            str(artifact_path),
            "--output-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "psi_report.json").is_file()
    assert (out / "psi_report.md").is_file()
    assert "psi_report" in result.output
