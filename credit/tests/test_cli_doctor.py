"""Hermetic tests for credit-css doctor (#191 / specs/016-credit-css-doctor)."""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from credit import __version__
from credit.cli import main

_LABELS = (
    "package_version:",
    "python_version:",
    "cwd:",
    "path_credit_data:",
    "path_competition_raw:",
    "env_CREDIT_PIPELINE_ARTIFACT_set:",
    "env_CREDIT_PIPELINE_ARTIFACT_file_exists:",
)

_BOOL_LABELS = (
    "path_credit_data:",
    "path_competition_raw:",
    "env_CREDIT_PIPELINE_ARTIFACT_set:",
    "env_CREDIT_PIPELINE_ARTIFACT_file_exists:",
)

_SECRET_MARKER = "doctor-secret-path-XYZ"
_SECRET_PATH = f"/tmp/{_SECRET_MARKER}/pipeline.joblib"


def _line_value(output: str, label: str) -> str:
    for line in output.splitlines():
        if line.startswith(label):
            return line[len(label) :].strip()
    raise AssertionError(f"missing label {label!r} in:\n{output}")


def test_doctor_prints_contract_labels_and_exits_zero() -> None:
    """doctor exits 0 with all contract labels; booleans are yes/no only."""
    result = CliRunner().invoke(main, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    for label in _LABELS:
        assert label in result.output, result.output
    assert _line_value(result.output, "package_version:") == __version__
    assert _line_value(result.output, "python_version:")
    assert _line_value(result.output, "cwd:")
    for label in _BOOL_LABELS:
        assert _line_value(result.output, label) in {"yes", "no"}


def test_doctor_help_mentions_readiness() -> None:
    result = CliRunner().invoke(main, ["doctor", "--help"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    combined = result.output.lower()
    assert "readiness" in combined or "diagnostic" in combined


def test_doctor_does_not_leak_artifact_env_value_or_path() -> None:
    """FR-007: planted path/secret never appears; set=yes, file_exists=no."""
    env = {**os.environ, "CREDIT_PIPELINE_ARTIFACT": _SECRET_PATH}
    result = CliRunner().invoke(main, ["doctor"], env=env, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert _line_value(result.output, "env_CREDIT_PIPELINE_ARTIFACT_set:") == "yes"
    assert (
        _line_value(result.output, "env_CREDIT_PIPELINE_ARTIFACT_file_exists:") == "no"
    )
    assert _SECRET_MARKER not in result.output
    assert _SECRET_PATH not in result.output
    assert _SECRET_MARKER not in (result.stderr or "")


def test_doctor_unset_artifact_reports_no_booleans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CREDIT_PIPELINE_ARTIFACT", raising=False)
    result = CliRunner().invoke(main, ["doctor"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert _line_value(result.output, "env_CREDIT_PIPELINE_ARTIFACT_set:") == "no"
    assert (
        _line_value(result.output, "env_CREDIT_PIPELINE_ARTIFACT_file_exists:") == "no"
    )
