"""Public-interface tests for the credit CSS CLI stub (#143)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_credit_module_help_identifies_css(tmp_path: Path) -> None:
    """python -m credit --help exits 0 and expands Credit Scoring System.

    cwd is a temp dir so the domain folder ``credit/`` at the repo root does not
    shadow the installable package as a PEP 420 namespace (same name).
    """
    result = subprocess.run(
        [sys.executable, "-m", "credit", "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    combined = f"{result.stdout}\n{result.stderr}"
    assert "Credit Scoring System" in combined


def test_credit_module_default_run_prints_css_stub(tmp_path: Path) -> None:
    """python -m credit (no args) exits 0 and prints the CSS stub message."""
    result = subprocess.run(
        [sys.executable, "-m", "credit"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "Credit Scoring System" in result.stdout
    assert "css-chapter5-mart-and-scoring.md" in result.stdout


def test_credit_cli_main_is_importable() -> None:
    """Console-script target credit.cli:main is importable and callable."""
    from credit.cli import main

    assert callable(main)


def test_credit_package_exposes_version(tmp_path: Path) -> None:
    """Package version is importable and printed by --version."""
    from credit import __version__

    assert isinstance(__version__, str)
    assert __version__

    result = subprocess.run(
        [sys.executable, "-m", "credit", "--version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert __version__ in result.stdout


def test_credit_does_not_import_investing_package(tmp_path: Path) -> None:
    """Importing credit must not load smartwealthai (no investing/SimFin coupling)."""
    probe = "\n".join(
        [
            "import sys",
            "assert 'smartwealthai' not in sys.modules",
            "import credit",
            "import credit.cli",
            "leaked = sorted(k for k in sys.modules if k.startswith('smart'))",
            "assert 'smartwealthai' not in sys.modules, leaked",
        ]
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
