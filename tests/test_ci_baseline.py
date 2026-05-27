"""Hermetic tests for CI baseline (issue #18). No network or AWS."""

from smartwealthai import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"
