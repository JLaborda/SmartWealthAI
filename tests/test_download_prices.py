"""Hermetic tests for SimFin shareprices price ingest (issue #59)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from smartwealthai.download_prices import cli_run
from smartwealthai.lake_paths import (
    curated_prices_path,
    curated_prices_snapshot_path,
    curated_universe_path,
    price_ingest_errors_path,
    simfin_bulk_path,
    yfinance_errors_path,
    yfinance_raw_path,
)
from smartwealthai.price_ingest import (
    CURATED_PRICE_COLUMNS,
    build_price_rows,
    load_raw_shareprices,
    load_universe_tickers,
    run_price_ingest,
    shareprices_raw_path,
    should_skip_artifact,
    write_curated_prices_snapshot,
)
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)
PRICE_DATE = date(2026, 6, 17)


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    """Copy fixture lake and build a demo universe snapshot."""
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    root = tmp_path / "lake"
    build_universe(root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    return root


def test_shareprices_raw_path_matches_spec_layout() -> None:
    path = shareprices_raw_path(Path("data"), snapshot_date=date(2026, 6, 18))
    assert path == Path(
        "data/raw/simfin/dataset=shareprices/variant=latest/market=us/"
        "as_of_date=2026-06-18/us-shareprices-latest.csv"
    )


def test_curated_prices_snapshot_path_matches_spec_layout() -> None:
    path = curated_prices_snapshot_path(Path("data"), run_date=date(2026, 6, 18))
    assert path == Path("data/curated/prices/run_date=2026-06-18/prices.parquet")


def test_curated_prices_path_matches_phase2_layout() -> None:
    path = curated_prices_path(Path("data"), ticker="AAPL", year=2026)
    assert path == Path("data/curated/prices/ticker=AAPL/year=2026/prices.parquet")


def test_yfinance_raw_path_matches_spec_layout() -> None:
    path = yfinance_raw_path(
        Path("data"),
        ticker="AAPL",
        endpoint="history",
        as_of_date=date(2026, 6, 18),
    )
    assert path == Path(
        "data/raw/yfinance/ticker=AAPL/endpoint=history/as_of_date=2026-06-18/history.json"
    )


def test_yfinance_errors_path_matches_spec_layout() -> None:
    path = yfinance_errors_path(Path("data"), run_date=date(2026, 6, 18))
    assert path == Path("data/raw/yfinance/download_runs/run_date=2026-06-18/errors.json")


def test_load_raw_shareprices_reads_fixture(lake: Path) -> None:
    frame = load_raw_shareprices(lake, snapshot_date=SNAPSHOT_DATE)
    assert "AAPL" in frame["Ticker"].values


def test_build_price_rows_uses_latest_on_or_before_run_date(lake: Path) -> None:
    shareprices = load_raw_shareprices(lake, snapshot_date=SNAPSHOT_DATE)
    rows, missing = build_price_rows(shareprices, ["AAPL"], run_date=RUN_DATE)

    assert missing == []
    assert len(rows) == 1
    assert rows[0]["price_date"] == PRICE_DATE.isoformat()
    assert rows[0]["adj_close"] == pytest.approx(273.5)


def test_build_price_rows_reports_missing_tickers(lake: Path) -> None:
    shareprices = load_raw_shareprices(lake, snapshot_date=SNAPSHOT_DATE)
    rows, missing = build_price_rows(shareprices, ["AAPL", "MISSING"], run_date=RUN_DATE)

    assert len(rows) == 1
    assert missing == ["MISSING"]


def test_build_price_rows_empty_when_run_date_before_all_prices(lake: Path) -> None:
    shareprices = load_raw_shareprices(lake, snapshot_date=SNAPSHOT_DATE)
    rows, missing = build_price_rows(shareprices, ["AAPL", "MSFT"], run_date=date(2026, 1, 1))

    assert rows == []
    assert missing == ["AAPL", "MSFT"]


def test_load_universe_tickers_raises_when_universe_missing(lake: Path) -> None:
    universe_path = curated_universe_path(lake, run_date=RUN_DATE)
    universe_path.unlink()

    with pytest.raises(FileNotFoundError, match="Universe not found"):
        load_universe_tickers(lake, run_date=RUN_DATE)


def test_run_price_ingest_returns_no_curated_path_when_all_tickers_missing(lake: Path) -> None:
    universe_path = curated_universe_path(lake, run_date=RUN_DATE)
    pd.DataFrame({"ticker": ["MISSING"]}).to_parquet(universe_path, index=False)

    ingest_run = run_price_ingest(data_dir=lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)

    assert ingest_run.included == 0
    assert ingest_run.curated_path is None
    assert ingest_run.missing_tickers == ["MISSING"]


def test_write_curated_prices_snapshot_has_expected_schema(lake: Path) -> None:
    shareprices = load_raw_shareprices(lake, snapshot_date=SNAPSHOT_DATE)
    rows, _ = build_price_rows(shareprices, ["AAPL"], run_date=RUN_DATE)
    path = write_curated_prices_snapshot(lake, run_date=RUN_DATE, rows=rows)

    prices = pd.read_parquet(path)
    assert list(prices.columns) == list(CURATED_PRICE_COLUMNS)


def test_should_skip_when_curated_snapshot_exists(lake: Path) -> None:
    run_price_ingest(data_dir=lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    curated = curated_prices_snapshot_path(lake, run_date=RUN_DATE)
    assert should_skip_artifact(curated, force=False) is True


def test_run_price_ingest_writes_curated_snapshot(lake: Path) -> None:
    ingest_run = run_price_ingest(
        data_dir=lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
    )

    assert ingest_run.included == 1
    assert ingest_run.missing_tickers == []
    assert ingest_run.curated_path is not None
    curated = pd.read_parquet(ingest_run.curated_path)
    assert curated.loc[curated["ticker"] == "AAPL", "adj_close"].iloc[0] == pytest.approx(273.5)


def test_run_skips_when_curated_snapshot_exists(lake: Path) -> None:
    run_price_ingest(data_dir=lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    second = run_price_ingest(data_dir=lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    assert second.run_skipped is True


def test_cli_records_missing_tickers(lake: Path) -> None:
    universe_path = curated_universe_path(lake, run_date=RUN_DATE)
    universe = pd.read_parquet(universe_path)
    extra = universe.iloc[[0]].copy()
    extra["ticker"] = "MISSING"
    pd.concat([universe, extra], ignore_index=True).to_parquet(universe_path, index=False)

    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--force",
        ]
    )

    assert exit_code == 0
    error_file = price_ingest_errors_path(lake, run_date=RUN_DATE)
    assert error_file.exists()
    errors = json.loads(error_file.read_text())
    assert errors == [
        {
            "ticker": "MISSING",
            "error": "no SimFin share price on or before run_date",
        }
    ]


def test_cli_run_end_to_end(lake: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
        ]
    )

    assert exit_code == 0
    curated = curated_prices_snapshot_path(lake, run_date=RUN_DATE)
    assert curated.exists()


def test_cli_skips_when_curated_snapshot_exists(lake: Path) -> None:
    assert (
        cli_run(
            [
                "--data-dir",
                str(lake),
                "--run-date",
                RUN_DATE.isoformat(),
                "--snapshot-date",
                SNAPSHOT_DATE.isoformat(),
            ]
        )
        == 0
    )

    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
        ]
    )

    assert exit_code == 0


def test_cli_fails_when_no_tickers_priced(lake: Path) -> None:
    universe_path = curated_universe_path(lake, run_date=RUN_DATE)
    pd.DataFrame({"ticker": ["MISSING"]}).to_parquet(universe_path, index=False)

    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--force",
        ]
    )

    assert exit_code == 1
    assert not curated_prices_snapshot_path(lake, run_date=RUN_DATE).exists()


def test_cli_warns_when_many_tickers_missing(lake: Path, caplog: pytest.LogCaptureFixture) -> None:
    universe_path = curated_universe_path(lake, run_date=RUN_DATE)
    universe = pd.read_parquet(universe_path)
    missing = pd.DataFrame({"ticker": [f"MISSING{i:02d}" for i in range(11)]})
    pd.concat([universe, missing], ignore_index=True).to_parquet(universe_path, index=False)

    with caplog.at_level("WARNING"):
        exit_code = cli_run(
            [
                "--data-dir",
                str(lake),
                "--run-date",
                RUN_DATE.isoformat(),
                "--snapshot-date",
                SNAPSHOT_DATE.isoformat(),
                "--force",
            ]
        )

    assert exit_code == 0
    assert "... and 1 more missing tickers" in caplog.text


def test_main_module_entrypoint(lake: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "smartwealthai.download_prices",
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert curated_prices_snapshot_path(lake, run_date=RUN_DATE).exists()


def test_cli_fails_when_shareprices_missing(lake: Path) -> None:
    raw_path = simfin_bulk_path(
        lake,
        dataset="shareprices",
        variant="latest",
        market="us",
        as_of_date=SNAPSHOT_DATE,
    )
    raw_path.unlink()

    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
        ]
    )

    assert exit_code == 1
