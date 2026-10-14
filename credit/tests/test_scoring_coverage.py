"""Hermetic coverage tests for #145 scoring modules (Codecov follow-up)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import joblib
import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

FIXTURE_MART = Path(__file__).parent / "fixtures" / "scoring_mart" / "applications.csv"


def _build_mart(tmp_path: Path) -> Path:
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
    return result.mart_path


# --- binning.py ---------------------------------------------------------------


def test_woe_transform_before_fit_raises() -> None:
    from credit.binning import WoeBinner

    with pytest.raises(RuntimeError, match="fit must be called"):
        WoeBinner().transform(pd.DataFrame({"x": [1.0, 2.0]}))


def test_woe_transform_missing_feature_raises() -> None:
    from credit.binning import WoeBinner

    X = pd.DataFrame({"a": np.linspace(0, 1, 20), "b": np.linspace(1, 2, 20)})
    y = pd.Series([0] * 10 + [1] * 10)
    binner = WoeBinner(n_bins=3).fit(X, y)
    with pytest.raises(KeyError, match="Missing feature"):
        binner.transform(pd.DataFrame({"a": [0.5]}))


def test_woe_all_null_series_treated_as_categorical() -> None:
    from credit.binning import WoeBinner, _treat_as_categorical

    assert _treat_as_categorical(pd.Series([pd.NA, pd.NA], dtype="Float64")) is True
    X = pd.DataFrame({"all_null": [np.nan, np.nan, np.nan, np.nan]})
    y = pd.Series([0, 1, 0, 1])
    out = WoeBinner().fit_transform(X, y)
    assert list(out.columns) == ["all_null"]


def test_woe_string_feature_is_categorical() -> None:
    from credit.binning import WoeBinner, _treat_as_categorical

    s = pd.Series(["a", "b", "a", "b", "a", "b"])
    assert _treat_as_categorical(s) is True
    y = pd.Series([0, 1, 0, 1, 0, 1])
    out = WoeBinner().fit_transform(pd.DataFrame({"cat": s}), y)
    assert out["cat"].notna().all()


def test_woe_constant_numeric_returns_zero_iv() -> None:
    from credit.binning import WoeBinner, _fit_numeric

    X = pd.DataFrame({"const": [1.0] * 12})
    y = pd.Series([0, 1] * 6)
    binner = WoeBinner().fit(X, y)
    assert binner.iv_by_feature["const"] == 0.0
    transformed = binner.transform(X)
    assert (transformed["const"] == 0.0).all()

    # Direct _fit_numeric: all-null / constant paths (public fit routes these to cat).
    empty_fb = _fit_numeric("x", pd.Series([np.nan, np.nan]), y.iloc[:2], n_bins=3)
    assert empty_fb.edges == ()
    assert empty_fb.woe_by_bin == (0.0,)
    const_fb = _fit_numeric("x", pd.Series([1.5, 1.5, 1.5]), y.iloc[:3], n_bins=3)
    assert const_fb.edges == ()


def test_woe_categorical_single_class_target() -> None:
    from credit.binning import WoeBinner

    X = pd.DataFrame({"cat": ["a", "b", "a", "b"]})
    y = pd.Series([0, 0, 0, 0])  # no bad
    binner = WoeBinner().fit(X, y)
    assert binner.feature_bins["cat"].woe_by_level == {}
    assert binner.iv_by_feature["cat"] == 0.0


def test_woe_numeric_single_class_and_empty_bins() -> None:
    from credit.binning import WoeBinner, _woe_for_bin_ids

    # Single-class y → early return in _woe_for_bin_ids
    woes, iv = _woe_for_bin_ids(np.array([0, 1, 0, 1]), np.array([0, 0, 0, 0]), n_bins=3)
    assert iv == 0.0
    assert woes == [0.0, 0.0, 0.0]

    # Empty bin id continues without updating
    woes2, iv2 = _woe_for_bin_ids(
        np.array([0, 0, 2, 2]),
        np.array([0, 1, 0, 1]),
        n_bins=3,  # bin 1 empty
    )
    assert woes2[1] == 0.0
    assert iv2 > 0.0 or iv2 == 0.0  # may be tiny; just exercise path

    X = pd.DataFrame({"x": np.linspace(0, 1, 16)})
    y = pd.Series([1] * 16)  # all bad
    binner = WoeBinner(n_bins=4).fit(X, y)
    assert binner.iv_by_feature["x"] == 0.0


def test_woe_apply_all_null_and_no_edges_numeric() -> None:
    from credit.binning import FeatureBins, WoeBinner, _apply_bins

    fb_null = FeatureBins(
        feature="x",
        kind="numeric",
        iv=0.0,
        edges=(0.5,),
        woe_by_bin=(0.1, 0.2),
        default_woe=-9.0,
    )
    out = _apply_bins(pd.Series([np.nan, np.nan]), fb_null)
    assert (out == -9.0).all()

    fb_no_edges = FeatureBins(
        feature="x",
        kind="numeric",
        iv=0.0,
        edges=(),
        woe_by_bin=(3.5,),
        default_woe=0.0,
    )
    out2 = _apply_bins(pd.Series([1.0, 2.0]), fb_no_edges)
    assert (out2 == 3.5).all()

    # High-cardinality numeric path through public API
    X = pd.DataFrame({"x": np.linspace(0, 10, 30)})
    y = pd.Series([0] * 15 + [1] * 15)
    transformed = WoeBinner(n_bins=5).fit_transform(X, y)
    assert transformed["x"].notna().all()


# --- feature_selection.py -----------------------------------------------------


def test_drop_high_null_empty_frame_and_threshold() -> None:
    from credit.feature_selection import drop_high_null_columns

    empty = pd.DataFrame(columns=["a", "b"])
    assert drop_high_null_columns(empty) == ["a", "b"]

    frame = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "keep": [1.0, 2.0, 3.0, 4.0, 5.0],
            "drop_me": [1.0, np.nan, np.nan, np.nan, np.nan],  # 80% null
            "protect_null": [np.nan] * 5,
        }
    )
    kept = drop_high_null_columns(frame, protect=("protect_null", "id"))
    assert "keep" in kept
    assert "drop_me" not in kept
    assert "protect_null" in kept
    assert "id" in kept


def test_candidate_features_after_null_drop_excludes_id_target() -> None:
    from credit.feature_selection import candidate_features

    frame = pd.DataFrame(
        {
            "customer_ID": ["a", "b", "c", "d", "e"],
            "target": [0, 1, 0, 1, 0],
            "AMT_INCOME": [1.0, 2.0, 3.0, 4.0, 5.0],
            "CONTRACT": ["x", "y", "x", "y", "x"],
            "almost_all_null": [1.0, np.nan, np.nan, np.nan, np.nan],  # 80% null
        }
    )
    feats = candidate_features(
        frame,
        application_id_column="customer_ID",
        target_column="target",
    )
    assert "AMT_INCOME" in feats
    assert "CONTRACT" in feats
    assert "almost_all_null" not in feats
    assert "customer_ID" not in feats
    assert "target" not in feats


def test_select_by_iv_keeps_threshold_and_orders_by_iv() -> None:
    from credit.feature_selection import select_by_iv

    kept = select_by_iv(
        {"weak": 0.01, "strong": 0.9, "mid": 0.05, "edge": 0.02},
        threshold=0.02,
    )
    assert kept == ["strong", "mid", "edge"]
    assert "weak" not in kept


# --- scoring_pipeline.py ------------------------------------------------------


def test_fit_raises_when_no_candidate_features(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from credit import scoring_pipeline as sp

    mart_path = _build_mart(tmp_path)
    monkeypatch.setattr(sp, "candidate_features", lambda *a, **k: [])
    with pytest.raises(ValueError, match="No candidate features"):
        sp.fit_scoring_pipeline(
            mart_path,
            tmp_path / "out",
            application_id_column="customer_ID",
            target_column="target",
            skip_mlflow=True,
        )


def test_fit_raises_when_no_features_pass_iv_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from credit import scoring_pipeline as sp

    mart_path = _build_mart(tmp_path)
    monkeypatch.setattr(sp, "select_by_iv", lambda *a, **k: [])
    with pytest.raises(ValueError, match="IV >="):
        sp.fit_scoring_pipeline(
            mart_path,
            tmp_path / "out",
            application_id_column="customer_ID",
            target_column="target",
            skip_mlflow=True,
        )


def test_load_pipeline_rejects_wrong_type(tmp_path: Path) -> None:
    from credit.scoring_pipeline import load_pipeline

    bad = tmp_path / "bad.joblib"
    joblib.dump({"not": "a pipeline"}, bad)
    with pytest.raises(TypeError, match="Unexpected artifact type"):
        load_pipeline(bad)


def test_load_mart_csv_pickle_and_unsupported(tmp_path: Path) -> None:
    from credit.scoring_pipeline import _load_mart

    csv_path = tmp_path / "m.csv"
    pd.DataFrame({"a": [1]}).to_csv(csv_path, index=False)
    assert len(_load_mart(csv_path)) == 1

    pkl_path = tmp_path / "m.pkl"
    pd.DataFrame({"a": [2]}).to_pickle(pkl_path)
    assert len(_load_mart(pkl_path)) == 1

    with pytest.raises(ValueError, match="Unsupported mart format"):
        _load_mart(tmp_path / "m.json")


def test_score_requires_feature_columns(tmp_path: Path) -> None:
    from credit.scoring_pipeline import ARTIFACT_NAME, fit_scoring_pipeline, score_applications

    mart_path = _build_mart(tmp_path)
    artifact_dir = tmp_path / "artifact"
    fit_scoring_pipeline(
        mart_path,
        artifact_dir,
        application_id_column="customer_ID",
        target_column="target",
        skip_mlflow=True,
        random_state=42,
    )
    thin = tmp_path / "thin.parquet"
    pd.DataFrame({"customer_ID": ["x"]}).to_parquet(thin, index=False)
    with pytest.raises(KeyError, match="missing required columns"):
        score_applications(artifact_dir / ARTIFACT_NAME, thin, tmp_path / "out.parquet")


# --- metrics / model / score_scaling / mlflow / cli ---------------------------


def test_ks_returns_zero_for_single_class() -> None:
    from credit.metrics import ks_statistic

    assert ks_statistic(np.array([0, 0, 0]), np.array([0.1, 0.2, 0.3])) == 0.0
    assert ks_statistic(np.array([1, 1, 1]), np.array([0.1, 0.2, 0.3])) == 0.0


def test_predict_pd_falls_back_when_class_one_absent() -> None:
    from credit.model import predict_pd

    model = MagicMock()
    model.classes_ = np.array([0])
    model.predict_proba.return_value = np.array([[0.7], [0.4]])
    X = pd.DataFrame({"f": [1.0, 2.0]})
    out = predict_pd(model, X)
    assert list(out) == pytest.approx([0.7, 0.4])


def test_score_scaling_to_from_dict_roundtrip() -> None:
    from credit.score_scaling import (
        SCORE_CLIP_MAX,
        SCORE_CLIP_MIN,
        ScoreScalingParams,
        pd_to_credit_score,
    )

    params = ScoreScalingParams(pdo=20.0, base_score=650.0, base_odds=20.0)
    restored = ScoreScalingParams.from_dict(params.to_dict())
    assert restored == params
    scores = pd_to_credit_score(np.array([0.1, 0.5]), restored)
    assert len(scores) == 2
    assert scores.min() >= SCORE_CLIP_MIN
    assert scores.max() <= SCORE_CLIP_MAX


def test_score_scaling_matches_book_pdo_good_odds() -> None:
    """PDO=20, base=650, good:bad=20; +PDO doubles good odds; higher = safer."""
    from credit.score_scaling import ScoreScalingParams, pd_to_credit_score

    params = ScoreScalingParams()
    factor = 20.0 / np.log(2.0)
    offset = 650.0 - factor * np.log(20.0)
    # At PD=0.5, good odds=1 → score = offset.
    mid = pd_to_credit_score(np.array([0.5]), params)[0]
    assert mid == pytest.approx(offset)
    # At good:bad = 20 → PD = 1/21, score = base_score.
    pd_at_base = 1.0 / (20.0 + 1.0)
    at_base = pd_to_credit_score(np.array([pd_at_base]), params)[0]
    assert at_base == pytest.approx(650.0)
    # Doubling good odds (+PDO points): odds 20 → 40 → PD = 1/41.
    pd_doubled = 1.0 / (40.0 + 1.0)
    doubled = pd_to_credit_score(np.array([pd_doubled]), params)[0]
    assert doubled == pytest.approx(650.0 + 20.0)
    # Extremes clip; higher PD → lower score.
    assert pd_to_credit_score(np.array([1e-9]), params)[0] == pytest.approx(1000.0)
    assert pd_to_credit_score(np.array([1.0 - 1e-9]), params)[0] == pytest.approx(250.0)
    safer, riskier = pd_to_credit_score(np.array([0.2, 0.8]), params)
    assert safer > riskier


def test_mlflow_resolve_uri_from_env_and_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from credit.mlflow_logging import _prepare_file_store, log_fit_run, resolve_tracking_uri

    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.chdir(tmp_path)
    assert resolve_tracking_uri(None).startswith("file:")

    monkeypatch.setenv("MLFLOW_TRACKING_URI", "file:///tmp/from-env")
    assert resolve_tracking_uri(None) == "file:///tmp/from-env"

    monkeypatch.delenv("MLFLOW_ALLOW_FILE_STORE", raising=False)
    _prepare_file_store("http://example")  # non-file: no env set
    assert os_environ_get_optional("MLFLOW_ALLOW_FILE_STORE") is None
    _prepare_file_store("file:///tmp/x")
    assert os_environ_get_optional("MLFLOW_ALLOW_FILE_STORE") == "true"

    artifact = tmp_path / "pipeline.joblib"
    joblib.dump({"ok": True}, artifact)
    run_id = log_fit_run(
        artifact_path=artifact,
        params={"k": "v"},
        metrics={"m": 1.0},
        tracking_uri=(tmp_path / "mlruns").as_uri(),
    )
    assert run_id


def os_environ_get_optional(key: str) -> str | None:
    import os

    return os.environ.get(key)


def test_cli_fit_prints_mlflow_run_id(tmp_path: Path) -> None:
    """Cover cli echo of MLflow run id (skip-mlflow path leaves it None)."""
    from credit.cli import main

    mart_path = _build_mart(tmp_path)
    tracking = tmp_path / "mlruns"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "fit",
            "--mart",
            str(mart_path),
            "--output-dir",
            str(tmp_path / "artifact"),
            "--application-id-column",
            "customer_ID",
            "--target-column",
            "target",
            "--mlflow-tracking-uri",
            tracking.as_uri(),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "MLflow run id:" in result.output
