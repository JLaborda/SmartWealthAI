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
from click.testing import CliRunner

from smartwealthai.download_price_history import cli_run, main
from smartwealthai.lake_paths import curated_prices_path
from smartwealthai.price_history_ingest import (
    CURATED_DAILY_PRICE_COLUMNS,
    PriceHistoryIngestRun,
    build_daily_price_rows,
    ensure_raw_shareprices_daily,
    load_raw_shareprices_daily,
    lookup_daily_adj_close,
    resolve_history_tickers,
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


def test_build_daily_price_rows_returns_empty_for_edge_cases(lake: Path) -> None:
    shareprices = load_raw_shareprices_daily(lake, snapshot_date=SNAPSHOT_DATE)

    assert build_daily_price_rows(shareprices, [], start_date=START_DATE, end_date=END_DATE) == []
    assert (
        build_daily_price_rows(pd.DataFrame(), ["AAPL"], start_date=START_DATE, end_date=END_DATE)
        == []
    )
    assert (
        build_daily_price_rows(
            shareprices,
            ["MISSING"],
            start_date=START_DATE,
            end_date=END_DATE,
        )
        == []
    )


def test_write_curated_daily_prices_empty_rows(lake: Path) -> None:
    written, skipped = write_curated_daily_prices(lake, [], force=False)
    assert written == []
    assert skipped == 0


def test_ensure_raw_shareprices_daily_skips_fresh_copy(lake: Path) -> None:
    raw_path = shareprices_daily_raw_path(lake, snapshot_date=SNAPSHOT_DATE)
    assert raw_path.exists()

    def fail_fetch(**_kwargs):
        msg = "network should not be called when raw partition is fresh"
        raise AssertionError(msg)

    result = ensure_raw_shareprices_daily(
        lake,
        snapshot_date=SNAPSHOT_DATE,
        refresh_days=7,
        force=False,
        fetch_csv=fail_fetch,
    )
    assert result == raw_path


def test_lookup_daily_adj_close_raises_when_as_of_before_window(lake: Path) -> None:
    run_price_history_ingest(
        data_dir=lake,
        tickers=["AAPL"],
        start_date=date(2025, 1, 1),
        end_date=END_DATE,
        snapshot_date=SNAPSHOT_DATE,
    )

    with pytest.raises(LookupError, match="on or before"):
        lookup_daily_adj_close(lake, ticker="AAPL", as_of_date=date(2025, 1, 1))


def test_resolve_history_tickers_requires_scope(lake: Path) -> None:
    with pytest.raises(ValueError, match="universe_run_date or explicit_tickers"):
        resolve_history_tickers(lake, universe_run_date=None, explicit_tickers=())


def test_cli_rejects_inverted_date_range(lake: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--data-dir",
            str(lake),
            "--ticker",
            "AAPL",
            "--start-date",
            "2026-06-30",
            "--end-date",
            "2026-01-01",
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--skip-download",
        ],
    )
    assert result.exit_code != 0
    assert "--start-date must be on or before --end-date" in result.output


def test_cli_requires_simfin_api_key_when_downloading(lake: Path) -> None:
    raw_path = shareprices_daily_raw_path(lake, snapshot_date=SNAPSHOT_DATE)
    raw_path.unlink()

    with patch.dict(os.environ, {}, clear=True):
        runner = CliRunner()
        result = runner.invoke(
            main,
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
            ],
        )

    assert result.exit_code != 0
    assert "SIMFIN_API_KEY is not set" in result.output


def test_cli_resolve_tickers_missing_universe(lake: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--data-dir",
            str(lake),
            "--universe-run-date",
            "2099-01-01",
            "--start-date",
            START_DATE.isoformat(),
            "--end-date",
            END_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--skip-download",
        ],
    )
    assert result.exit_code != 0
    assert "Universe not found" in result.output


def test_cli_handles_download_os_error(lake: Path) -> None:
    with patch.dict(os.environ, {"SIMFIN_API_KEY": "test-key"}):
        with patch(
            "smartwealthai.download_price_history.ensure_raw_shareprices_daily",
            side_effect=OSError("disk full"),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
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
                ],
            )

    assert result.exit_code != 0
    assert "disk full" in result.output


def test_cli_fails_when_no_rows_normalized(lake: Path) -> None:
    exit_code = cli_run(
        [
            "--data-dir",
            str(lake),
            "--ticker",
            "MISSING",
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


def test_cli_warns_when_many_partitions_written(
    lake: Path, caplog: pytest.LogCaptureFixture
) -> None:
    many_paths = [curated_prices_path(lake, ticker=f"T{i:02d}", year=2026) for i in range(11)]
    fake_run = PriceHistoryIngestRun(
        partitions_written=many_paths,
        partitions_skipped=0,
        row_count=11,
    )

    with patch(
        "smartwealthai.download_price_history.run_price_history_ingest",
        return_value=fake_run,
    ):
        with caplog.at_level("WARNING"):
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

    assert exit_code == 0
    assert "... and 1 more partitions" in caplog.text
