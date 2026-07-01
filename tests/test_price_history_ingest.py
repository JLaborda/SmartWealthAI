"""Hermetic tests for SimFin shareprices/daily price history ingest (issue #88)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from smartwealthai.download_price_history import cli_run
from smartwealthai.lake_paths import curated_prices_path
from smartwealthai.price_history_ingest import (
    CURATED_DAILY_PRICE_COLUMNS,
    build_daily_price_rows,
    load_raw_shareprices_daily,
    lookup_daily_adj_close,
    run_price_history_ingest,
    shareprices_daily_raw_path,
    write_curated_daily_prices,
)
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 6, 30)


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    """Copy fixture lake and build a demo universe snapshot."""
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    root = tmp_path / "lake"
    build_universe(root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    return root


def test_shareprices_daily_raw_path_matches_spec_layout() -> None:
    path = shareprices_daily_raw_path(Path("data"), snapshot_date=date(2026, 6, 18))
    assert path == Path(
        "data/raw/simfin/dataset=shareprices/variant=daily/market=us/"
        "as_of_date=2026-06-18/us-shareprices-daily.csv"
    )


def test_load_raw_shareprices_daily_reads_fixture(lake: Path) -> None:
    frame = load_raw_shareprices_daily(lake, snapshot_date=SNAPSHOT_DATE)
    assert "AAPL" in frame["Ticker"].values
    assert "MSFT" in frame["Ticker"].values


def test_build_daily_price_rows_filters_tickers_and_date_range(lake: Path) -> None:
    shareprices = load_raw_shareprices_daily(lake, snapshot_date=SNAPSHOT_DATE)
    rows = build_daily_price_rows(
        shareprices,
        ["AAPL", "MISSING"],
        start_date=START_DATE,
        end_date=END_DATE,
    )

    assert len(rows) == 3
    assert {row["ticker"] for row in rows} == {"AAPL"}
    assert rows[-1]["adj_close"] == pytest.approx(273.5)


def test_write_curated_daily_prices_partitions_by_ticker_year(lake: Path) -> None:
    shareprices = load_raw_shareprices_daily(lake, snapshot_date=SNAPSHOT_DATE)
    rows = build_daily_price_rows(
        shareprices,
        ["AAPL", "MSFT"],
        start_date=date(2025, 1, 1),
        end_date=END_DATE,
    )
    written, skipped = write_curated_daily_prices(lake, rows, force=False)

    assert skipped == 0
    assert len(written) == 4
    aapl_2026 = curated_prices_path(lake, ticker="AAPL", year=2026)
    assert aapl_2026 in written
    prices = pd.read_parquet(aapl_2026)
    assert list(prices.columns) == list(CURATED_DAILY_PRICE_COLUMNS)
    assert len(prices) == 3


def test_write_curated_daily_prices_skips_existing_partitions(lake: Path) -> None:
    shareprices = load_raw_shareprices_daily(lake, snapshot_date=SNAPSHOT_DATE)
    rows = build_daily_price_rows(
        shareprices,
        ["AAPL"],
        start_date=START_DATE,
        end_date=END_DATE,
    )
    write_curated_daily_prices(lake, rows, force=False)
    _, skipped = write_curated_daily_prices(lake, rows, force=False)
    assert skipped == 1


def test_lookup_daily_adj_close_returns_latest_on_or_before_date(lake: Path) -> None:
    run_price_history_ingest(
        data_dir=lake,
        tickers=["AAPL"],
        start_date=date(2025, 1, 1),
        end_date=END_DATE,
        snapshot_date=SNAPSHOT_DATE,
    )

    assert lookup_daily_adj_close(
        lake, ticker="AAPL", as_of_date=date(2026, 6, 17)
    ) == pytest.approx(273.5)
    assert lookup_daily_adj_close(
        lake, ticker="AAPL", as_of_date=date(2026, 6, 18)
    ) == pytest.approx(273.5)


def test_lookup_daily_adj_close_raises_when_no_history(lake: Path) -> None:
    with pytest.raises(LookupError, match="No daily price history"):
        lookup_daily_adj_close(lake, ticker="AAPL", as_of_date=RUN_DATE)


def test_run_price_history_ingest_end_to_end(lake: Path) -> None:
    result = run_price_history_ingest(
        data_dir=lake,
        tickers=["AAPL", "MSFT"],
        start_date=date(2025, 1, 1),
        end_date=END_DATE,
        snapshot_date=SNAPSHOT_DATE,
    )

    assert result.row_count == 6
    assert len(result.partitions_written) == 4
    assert curated_prices_path(lake, ticker="MSFT", year=2025).exists()


def test_cli_download_price_history_end_to_end(lake: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--universe-run-date",
            RUN_DATE.isoformat(),
            "--start-date",
            START_DATE.isoformat(),
            "--end-date",
            END_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--skip-download",
        ]
    )

    assert exit_code == 0
    assert curated_prices_path(lake, ticker="AAPL", year=2026).exists()


def test_cli_fails_when_raw_daily_missing(lake: Path) -> None:
    raw_path = shareprices_daily_raw_path(lake, snapshot_date=SNAPSHOT_DATE)
    raw_path.unlink()

    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--ticker",
            "AAPL",
            "--start-date",
            START_DATE.isoformat(),
            "--end-date",
            END_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--skip-download",
        ]
    )

    assert exit_code == 1


def test_cli_downloads_raw_when_not_skipped(lake: Path, tmp_path: Path) -> None:
    raw_path = shareprices_daily_raw_path(lake, snapshot_date=SNAPSHOT_DATE)
    fixture_csv = raw_path.read_text()
    raw_path.unlink()

    def fake_fetch(**_kwargs):
        dest = tmp_path / "us-shareprices-daily.csv"
        dest.write_text(fixture_csv)
        return dest

    with patch.dict(os.environ, {"SIMFIN_API_KEY": "test-key"}):
        with patch(
            "smartwealthai.price_history_ingest.fetch_dataset_csv",
            side_effect=fake_fetch,
        ):
            exit_code = cli_run(
                [
                    "--data-dir",
                    str(lake),
                    "--ticker",
                    "AAPL",
                    "--start-date",
                    START_DATE.isoformat(),
                    "--end-date",
                    END_DATE.isoformat(),
                    "--snapshot-date",
                    SNAPSHOT_DATE.isoformat(),
                ]
            )

    assert exit_code == 0
    assert raw_path.exists()


def test_main_module_entrypoint(lake: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "smartwealthai.download_price_history",
            "--data-dir",
            str(lake),
            "--ticker",
            "AAPL",
            "--start-date",
            START_DATE.isoformat(),
            "--end-date",
            END_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--skip-download",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert curated_prices_path(lake, ticker="AAPL", year=2026).exists()
