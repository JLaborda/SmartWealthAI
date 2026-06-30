"""Hermetic tests for lake root URI resolution and file-backend I/O."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from smartwealthai.cli_lake import resolve_cli_data_dir, resolve_cli_lake_root
from smartwealthai.lake_paths import curated_portfolio_path
from smartwealthai.lake_root import resolve_lake_root
from smartwealthai.score_universe import cli_run as score_cli_run

RUN_DATE = date(2026, 6, 18)
FIXTURE_LAKE = Path("tests/fixtures/lake")


def test_resolve_lake_root_file_uri_returns_usable_root(tmp_path: Path) -> None:
    lake_dir = tmp_path / "lake"
    lake_dir.mkdir()
    root = resolve_lake_root(f"file://{lake_dir}")
    expected = curated_portfolio_path(lake_dir, run_date=RUN_DATE)
    assert root.curated_portfolio_path(run_date=RUN_DATE) == expected
    assert root.as_path() == lake_dir.resolve()


def test_resolve_lake_root_bare_path_equivalent_to_file_uri(tmp_path: Path) -> None:
    lake_dir = tmp_path / "lake"
    lake_dir.mkdir()
    from_uri = resolve_lake_root(f"file://{lake_dir}")
    from_bare = resolve_lake_root(str(lake_dir))
    assert from_uri.as_path() == from_bare.as_path()


def test_lake_root_parquet_round_trip(tmp_path: Path) -> None:
    root = resolve_lake_root(str(tmp_path / "lake"))
    path = root.curated_portfolio_path(run_date=RUN_DATE)
    frame = pd.DataFrame({"ticker": ["AAPL"], "weight": [1.0]})
    root.write_parquet(path, frame)
    loaded = root.read_parquet(path)
    pd.testing.assert_frame_equal(loaded, frame)


def test_resolve_lake_root_rejects_unsupported_scheme() -> None:
    with pytest.raises(ValueError, match="Unsupported lake root URI scheme"):
        resolve_lake_root("ftp://example.com/lake")


def test_resolve_lake_root_rejects_empty_uri() -> None:
    with pytest.raises(ValueError, match="Lake root URI is required"):
        resolve_lake_root(None)
    with pytest.raises(ValueError, match="Lake root URI is required"):
        resolve_lake_root("   ")


def test_resolve_lake_root_rejects_invalid_s3_uri() -> None:
    with pytest.raises(ValueError, match="Invalid S3 lake root URI"):
        resolve_lake_root("s3://")


def test_resolve_cli_lake_root_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    flag_path = tmp_path / "from-flag"
    data_dir_path = tmp_path / "from-data-dir"
    swai_path = tmp_path / "from-swai"
    for path in (flag_path, data_dir_path, swai_path):
        path.mkdir()

    monkeypatch.setenv("SMARTWEALTHAI_DATA_DIR", str(swai_path))

    flag_root = resolve_cli_lake_root(
        lake_root_uri=f"file://{flag_path}",
        data_dir=data_dir_path,
    )
    assert flag_root.as_path() == flag_path.resolve()

    data_root = resolve_cli_lake_root(lake_root_uri=None, data_dir=data_dir_path)
    assert data_root.as_path() == data_dir_path.resolve()

    env_root = resolve_cli_lake_root(lake_root_uri=None, data_dir=None)
    assert env_root.as_path() == swai_path.resolve()

    monkeypatch.delenv("SMARTWEALTHAI_DATA_DIR", raising=False)
    default_root = resolve_cli_lake_root(lake_root_uri=None, data_dir=None)
    assert default_root.as_path() == Path("data").resolve()


def test_resolve_cli_data_dir_returns_path(tmp_path: Path) -> None:
    lake_dir = tmp_path / "lake"
    lake_dir.mkdir()
    path = resolve_cli_data_dir(lake_root_uri=f"file://{lake_dir}", data_dir=None)
    assert path == lake_dir.resolve()


@pytest.fixture
def scored_lake(tmp_path: Path) -> Path:
    """Minimal prepared lake for score-universe CLI regression."""
    from smartwealthai.normalize_simfin import cli_run as normalize_cli_run
    from smartwealthai.price_ingest import run_price_ingest
    from smartwealthai.universe_builder import build_universe

    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    root = tmp_path / "lake"
    build_universe(root, run_date=RUN_DATE, snapshot_date=RUN_DATE)
    normalize_cli_run(
        [
            "--data-dir",
            str(root),
            "--snapshot-date",
            RUN_DATE.isoformat(),
            "--universe-run-date",
            RUN_DATE.isoformat(),
        ]
    )
    run_price_ingest(data_dir=root, run_date=RUN_DATE, snapshot_date=RUN_DATE)
    return root


def test_cli_score_universe_accepts_lake_root_uri_flag(scored_lake: Path) -> None:
    exit_code = score_cli_run(
        [
            "--lake-root-uri",
            f"file://{scored_lake}",
            "--run-date",
            RUN_DATE.isoformat(),
            "--portfolio-size",
            "3",
        ]
    )
    assert exit_code == 0


def test_cli_score_universe_data_dir_still_works(scored_lake: Path) -> None:
    exit_code = score_cli_run(
        [
            "--data-dir",
            str(scored_lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--portfolio-size",
            "3",
        ]
    )
    assert exit_code == 0


def test_cli_score_universe_rejects_malformed_lake_root_uri(scored_lake: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        __import__("smartwealthai.score_universe", fromlist=["main"]).main,
        [
            "--lake-root-uri",
            "ftp://bad",
            "--run-date",
            RUN_DATE.isoformat(),
        ],
    )
    assert result.exit_code != 0
    assert "Unsupported lake root URI scheme" in result.output


def test_s3_lake_root_parses_without_local_path() -> None:
    root = resolve_lake_root("s3://smartwealthai-dev-lake/data/")
    assert root.backend == "s3"
    assert root.s3_bucket == "smartwealthai-dev-lake"
    assert root.s3_prefix == "data/"
    with pytest.raises(TypeError, match="local Path"):
        root.as_path()
