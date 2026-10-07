"""Public-interface tests for local PSI data-drift CLI (Friday MUST)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
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


def test_classify_psi_thresholds() -> None:
    from credit.psi import classify_psi

    assert classify_psi(0.05) == "stable"
    assert classify_psi(0.15) == "shift"
    assert classify_psi(0.25) == "severe"
    assert classify_psi(0.10) == "shift"  # exclusive upper bound for stable


def test_compute_psi_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    from credit import psi as psi_mod
    from credit.psi import compute_psi

    empty = pd.Series([], dtype=float)
    assert np.isnan(compute_psi(empty, pd.Series([1.0, 2.0])))
    assert np.isnan(compute_psi(pd.Series([1.0, 2.0]), empty))

    # Shared edges: identical draws → near-zero PSI
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=200))
    assert compute_psi(x, x) < 0.01

    # Degenerate qcut path (ValueError) — constant ref vs constant / varying recent.
    def _boom(*_args, **_kwargs):
        raise ValueError("Bin edges must be unique")

    monkeypatch.setattr(psi_mod.pd, "qcut", _boom)
    constant = pd.Series([1.0] * 20)
    assert compute_psi(constant, constant) == 0.0
    assert compute_psi(constant, pd.Series(np.linspace(0, 1, 20))) == float("inf")


def test_top_iv_features_falls_back_to_feature_names_order() -> None:
    from credit.psi import top_iv_features

    pipeline = SimpleNamespace(
        wrap_notes={},
        feature_names=["b", "a", "c"],
    )
    assert top_iv_features(pipeline, limit=2) == ["b", "a"]

    pipeline_iv = SimpleNamespace(
        wrap_notes={"iv_by_feature": {"a": 0.1, "b": 0.5, "c": 0.2}},
        feature_names=["a", "b", "c"],
    )
    assert top_iv_features(pipeline_iv, limit=2) == ["b", "c"]


def test_apply_synthetic_drift_skips_missing_and_zero_std() -> None:
    from credit.psi import apply_synthetic_drift

    frame = pd.DataFrame({"keep": [1.0, 1.0, 1.0], "other": [0.0, 1.0, 2.0]})
    out, shifted = apply_synthetic_drift(
        frame,
        ["missing", "keep"],
        n_shift=2,
        seed=0,
    )
    assert shifted == ["missing", "keep"]
    assert "missing" not in out.columns
    # zero-std column still gets a shock (std fallback 1.0)
    assert not out["keep"].equals(frame["keep"])


def test_run_psi_check_reference_recent_and_guards(tmp_path: Path) -> None:
    """--reference/--recent path, --no-pd, and CLI mutual-exclusion guards."""
    from credit.psi import run_psi_check

    mart_path, artifact_path = _build_mart_and_artifact(tmp_path)
    frame = pd.read_parquet(mart_path)
    mid = len(frame) // 2
    ref_path = tmp_path / "reference.parquet"
    recent_path = tmp_path / "recent.parquet"
    frame.iloc[:mid].to_parquet(ref_path, index=False)
    frame.iloc[mid:].to_parquet(recent_path, index=False)

    report = run_psi_check(
        artifact_path=artifact_path,
        output_dir=tmp_path / "psi_ref_recent",
        reference_path=ref_path,
        recent_path=recent_path,
        include_pd=False,
    )
    names = {c.column for c in report.columns}
    assert "credit_score" in names
    assert "pd" not in names
    assert (tmp_path / "psi_ref_recent" / "psi_report.md").is_file()
    # Shifted-features line omitted when not synthetic
    md = (tmp_path / "psi_ref_recent" / "psi_report.md").read_text(encoding="utf-8")
    assert "Shifted features" not in md

    with pytest.raises(ValueError, match="severe_threshold"):
        run_psi_check(
            mart_path=mart_path,
            artifact_path=artifact_path,
            output_dir=tmp_path / "bad_thresh",
            stable_threshold=0.3,
            severe_threshold=0.1,
        )

    with pytest.raises(ValueError, match="either --mart or --reference"):
        run_psi_check(
            mart_path=mart_path,
            artifact_path=artifact_path,
            output_dir=tmp_path / "both",
            reference_path=ref_path,
            recent_path=recent_path,
        )

    with pytest.raises(ValueError, match="both --reference and --recent"):
        run_psi_check(
            artifact_path=artifact_path,
            output_dir=tmp_path / "neither",
        )


def test_run_psi_check_skips_monitored_column_missing_from_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a monitored column is absent on one batch, PSI skips it (no crash)."""
    from credit import psi as psi_mod
    from credit.psi import run_psi_check

    mart_path, artifact_path = _build_mart_and_artifact(tmp_path)
    real_score = psi_mod._score_frame
    calls = {"n": 0}

    def _score_drop_pd(pipeline, frame):
        scored = real_score(pipeline, frame)
        calls["n"] += 1
        # Drop pd only on the recent batch (second score call).
        if calls["n"] == 2:
            return scored.drop(columns=["pd"])
        return scored

    monkeypatch.setattr(psi_mod, "_score_frame", _score_drop_pd)
    report = run_psi_check(
        mart_path=mart_path,
        artifact_path=artifact_path,
        output_dir=tmp_path / "psi_skip",
        include_pd=True,
    )
    assert "pd" not in {c.column for c in report.columns}
    assert "credit_score" in {c.column for c in report.columns}
