"""Hermetic tests for fundamentals download helpers.

Covers universe loading, raw-zone path layout, and skip/force cache semantics.
Network integration tests are intentionally excluded from PR CI; see
``docs/mvp/guides/download-fundamentals.md``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from smartwealthai.download_fundamentals import should_skip
from smartwealthai.lake_paths import (
    artifact_paths,
    companyfacts_path,
    edgartools_statement_path,
    errors_path,
    pad_cik,
)
from smartwealthai.universe import load_universe, resolve_universe_file


def test_pad_cik_zero_fills_to_ten_digits() -> None:
    assert pad_cik("320193") == "0000320193"


def test_companyfacts_path_matches_spec_layout() -> None:
    path = companyfacts_path(Path("data"), "320193", date(2026, 6, 7))
    assert path == Path(
        "data/raw/sec_edgar/cik=0000320193/endpoint=companyfacts/"
        "as_of_date=2026-06-07/response.json"
    )


def test_edgartools_statement_paths_match_spec_layout() -> None:
    path = edgartools_statement_path(Path("data"), "320193", date(2026, 6, 7), "income_statement")
    assert path == Path(
        "data/raw/edgartools/cik=0000320193/as_of_date=2026-06-07/income_statement_annual.parquet"
    )


def test_errors_path_matches_spec_layout() -> None:
    path = errors_path(Path("data"), date(2026, 6, 7))
    assert path == Path("data/raw/download_runs/as_of_date=2026-06-07/errors.json")


def test_artifact_paths_returns_four_targets_per_cik() -> None:
    paths = artifact_paths(Path("data"), "320193", date(2026, 6, 7))
    assert len(paths) == 4


def test_edgartools_statement_path_rejects_unknown_statement() -> None:
    with pytest.raises(ValueError, match="Unknown statement"):
        edgartools_statement_path(Path("data"), "320193", date(2026, 6, 7), "unknown")


def test_should_skip_when_file_exists_and_not_forced(tmp_path: Path) -> None:
    target = tmp_path / "response.json"
    target.write_text("{}")
    assert should_skip(target, force=False) is True


def test_should_not_skip_when_force_enabled(tmp_path: Path) -> None:
    target = tmp_path / "response.json"
    target.write_text("{}")
    assert should_skip(target, force=True) is False


def test_should_not_skip_when_file_missing(tmp_path: Path) -> None:
    target = tmp_path / "response.json"
    assert should_skip(target, force=False) is False


def test_load_universe_dow30_preset_has_thirty_rows() -> None:
    entries = load_universe(universe="dow30")
    assert len(entries) == 30
    assert entries[0].ticker
    assert len(entries[0].cik) == 10


def test_load_universe_from_explicit_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "mini.csv"
    csv_path.write_text("ticker,cik\nAAPL,0000320193\nMSFT,0000789019\n")
    entries = load_universe(universe_file=csv_path)
    assert [(entry.ticker, entry.cik) for entry in entries] == [
        ("AAPL", "0000320193"),
        ("MSFT", "0000789019"),
    ]


def test_resolve_universe_file_requires_preset_or_path() -> None:
    with pytest.raises(ValueError, match="Provide --universe or --universe-file"):
        resolve_universe_file(None, None)


def test_resolve_universe_file_rejects_unknown_preset() -> None:
    with pytest.raises(ValueError, match="Unknown universe preset"):
        resolve_universe_file("nasdaq100", None)
