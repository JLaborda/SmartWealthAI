"""Hermetic tests for PIT fundamentals loading (issue #44)."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from smartwealthai.lake_paths import curated_prices_snapshot_path, curated_universe_path, pad_cik
from smartwealthai.pit_fundamentals import (
    MetricsInputError,
    _cik_from_partition_path,
    _fundamentals_paths_for_ciks,
    _optional_float,
    _read_fundamentals_partition,
    _resolve_show_progress,
    _select_pit_fundamentals,
    _select_pit_fundamentals_by_period,
    _ticker_progress_iter,
    compute_metrics_for_ticker,
    compute_metrics_for_tickers,
    load_pit_fundamentals_bulk,
    load_pit_fundamentals_history,
    load_pit_fundamentals_row,
    load_ticker_price_row,
    resolve_ticker_cik,
)

RUN_DATE = date(2026, 6, 18)
CIK = pad_cik("320193")


def _write_universe(lake: Path, *, rows: list[dict[str, object]]) -> None:
    path = curated_universe_path(lake, run_date=RUN_DATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_fundamentals(lake: Path, *, period: str, row: dict[str, object]) -> None:
    path = (
        lake
        / "curated"
        / "fundamentals"
        / f"cik={CIK}"
        / f"period={period}"
        / "fundamentals.parquet"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_parquet(path, index=False)


def _write_prices(lake: Path, *, rows: list[dict[str, object]]) -> None:
    path = curated_prices_snapshot_path(lake, run_date=RUN_DATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _base_fundamentals_row(**overrides: object) -> dict[str, object]:
    row = {
        "as_of_date": pd.Timestamp("2026-06-01"),
        "fiscal_period_end": pd.Timestamp("2024-09-28"),
        "version_id": 1,
        "statement_variant": "ttm",
        "ebit": 100.0,
        "current_assets": 200.0,
        "current_liabilities": 80.0,
        "cash": 20.0,
        "short_term_debt": 0.0,
        "ppe_net": 50.0,
        "shares_outstanding": 10.0,
        "long_term_debt": 30.0,
        "preferred_equity": 0.0,
        "minority_interest": 0.0,
    }
    row.update(overrides)
    return row


@pytest.fixture
def pit_lake(tmp_path: Path) -> Path:
    lake = tmp_path / "lake"
    lake.mkdir()
    _write_universe(lake, rows=[{"ticker": "AAPL", "cik": CIK}])
    _write_fundamentals(lake, period="2024Q4", row=_base_fundamentals_row())
    _write_prices(
        lake,
        rows=[
            {
                "run_date": RUN_DATE.isoformat(),
                "ticker": "AAPL",
                "price_date": RUN_DATE.isoformat(),
                "close": 10.0,
                "adj_close": 10.0,
                "volume": 1,
            }
        ],
    )
    return lake


def test_resolve_ticker_cik_raises_when_universe_missing(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()

    with pytest.raises(MetricsInputError, match="No universe snapshot"):
        resolve_ticker_cik(lake, ticker="AAPL", run_date=RUN_DATE)


def test_resolve_ticker_cik_raises_when_ticker_not_in_universe(pit_lake: Path) -> None:
    with pytest.raises(MetricsInputError, match="not in universe"):
        resolve_ticker_cik(pit_lake, ticker="MISSING", run_date=RUN_DATE)


def test_load_pit_fundamentals_raises_when_cik_dir_missing(pit_lake: Path) -> None:
    shutil.rmtree(pit_lake / "curated" / "fundamentals")

    with pytest.raises(MetricsInputError, match="No curated fundamentals"):
        load_pit_fundamentals_row(pit_lake, ticker="AAPL", as_of_date=RUN_DATE)


def test_load_pit_fundamentals_raises_when_all_partitions_empty(pit_lake: Path) -> None:
    empty_path = (
        pit_lake
        / "curated"
        / "fundamentals"
        / f"cik={CIK}"
        / "period=2024Q3"
        / "fundamentals.parquet"
    )
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=["as_of_date", "version_id", "ebit"]).to_parquet(empty_path, index=False)
    shutil.rmtree(pit_lake / "curated" / "fundamentals" / f"cik={CIK}" / "period=2024Q4")

    with pytest.raises(MetricsInputError, match="No curated fundamentals"):
        load_pit_fundamentals_row(pit_lake, ticker="AAPL", as_of_date=RUN_DATE)


def test_load_pit_fundamentals_raises_when_no_pit_row_on_date(pit_lake: Path) -> None:
    _write_fundamentals(
        pit_lake,
        period="2024Q4",
        row=_base_fundamentals_row(as_of_date=pd.Timestamp("2027-01-01")),
    )

    with pytest.raises(MetricsInputError, match="No PIT fundamentals"):
        load_pit_fundamentals_row(pit_lake, ticker="AAPL", as_of_date=RUN_DATE)


def test_load_ticker_price_row_raises_when_snapshot_missing(pit_lake: Path) -> None:
    path = curated_prices_snapshot_path(pit_lake, run_date=RUN_DATE)
    path.unlink()

    with pytest.raises(MetricsInputError, match="Curated prices not found"):
        load_ticker_price_row(pit_lake, ticker="AAPL", run_date=RUN_DATE)


def test_load_ticker_price_row_raises_when_ticker_missing(pit_lake: Path) -> None:
    with pytest.raises(MetricsInputError, match="No curated price"):
        load_ticker_price_row(pit_lake, ticker="MISSING", run_date=RUN_DATE)


def test_optional_float_treats_nan_as_none() -> None:
    assert _optional_float(float("nan")) is None


def test_compute_metrics_for_ticker_maps_nan_fields_to_missing_inputs(pit_lake: Path) -> None:
    _write_fundamentals(
        pit_lake,
        period="2024Q4",
        row=_base_fundamentals_row(ebit=float("nan")),
    )

    result = compute_metrics_for_ticker(pit_lake, ticker="AAPL", as_of_date=RUN_DATE)

    assert result.ebit is None
    assert "missing_inputs" in result.flags


def test_cik_from_partition_path_raises_when_layout_invalid(tmp_path: Path) -> None:
    bad_path = tmp_path / "fundamentals.parquet"

    with pytest.raises(MetricsInputError, match="Could not resolve CIK"):
        _cik_from_partition_path(bad_path)


def test_select_pit_fundamentals_returns_empty_frame_unchanged() -> None:
    assert _select_pit_fundamentals(pd.DataFrame(), RUN_DATE).empty


def test_fundamentals_paths_skips_missing_cik_directories(pit_lake: Path) -> None:
    paths = _fundamentals_paths_for_ciks(
        pit_lake,
        {CIK, pad_cik("9999999999")},
    )

    assert len(paths) == 1


def test_read_fundamentals_partition_returns_none_for_empty_file(pit_lake: Path) -> None:
    empty_path = (
        pit_lake
        / "curated"
        / "fundamentals"
        / f"cik={CIK}"
        / "period=2024Q3"
        / "fundamentals.parquet"
    )
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=["as_of_date", "version_id", "ebit"]).to_parquet(empty_path, index=False)

    assert _read_fundamentals_partition(empty_path) is None


def test_load_pit_fundamentals_bulk_returns_empty_when_no_partitions(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()

    assert load_pit_fundamentals_bulk(lake, ciks={CIK}, as_of_date=RUN_DATE) == {}


def test_load_pit_fundamentals_bulk_returns_empty_when_all_partitions_empty(
    pit_lake: Path,
) -> None:
    shutil.rmtree(pit_lake / "curated" / "fundamentals" / f"cik={CIK}" / "period=2024Q4")
    empty_path = (
        pit_lake
        / "curated"
        / "fundamentals"
        / f"cik={CIK}"
        / "period=2024Q3"
        / "fundamentals.parquet"
    )
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=["as_of_date", "version_id", "ebit"]).to_parquet(empty_path, index=False)

    assert load_pit_fundamentals_bulk(pit_lake, ciks={CIK}, as_of_date=RUN_DATE) == {}


def test_load_pit_fundamentals_bulk_skips_empty_partitions_and_uses_progress(
    pit_lake: Path,
) -> None:
    empty_path = (
        pit_lake
        / "curated"
        / "fundamentals"
        / f"cik={CIK}"
        / "period=2024Q3"
        / "fundamentals.parquet"
    )
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=["as_of_date", "version_id", "ebit"]).to_parquet(empty_path, index=False)

    loaded = load_pit_fundamentals_bulk(
        pit_lake,
        ciks={CIK},
        as_of_date=RUN_DATE,
        show_progress=True,
    )

    assert CIK in loaded


def test_resolve_show_progress_honors_explicit_flag() -> None:
    assert _resolve_show_progress(True) is True
    assert _resolve_show_progress(False) is False


def test_ticker_progress_iter_yields_all_tickers_when_enabled() -> None:
    tickers = ["AAPL", "MSFT"]

    assert list(_ticker_progress_iter(tickers, enabled=True)) == tickers


def test_compute_metrics_for_tickers_raises_when_universe_missing(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()

    with pytest.raises(MetricsInputError, match="No universe snapshot"):
        compute_metrics_for_tickers(lake, tickers=["AAPL"], as_of_date=RUN_DATE)


def test_compute_metrics_for_tickers_skips_missing_inputs(pit_lake: Path) -> None:
    other_cik = pad_cik("9999999999")
    _write_universe(
        pit_lake,
        rows=[
            {"ticker": "AAPL", "cik": CIK},
            {"ticker": "NOFUND", "cik": other_cik},
            {"ticker": "NOPRICE", "cik": pad_cik("8888888888")},
        ],
    )
    noprice_cik = pad_cik("8888888888")
    noprice_path = (
        pit_lake
        / "curated"
        / "fundamentals"
        / f"cik={noprice_cik}"
        / "period=2024Q4"
        / "fundamentals.parquet"
    )
    noprice_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([_base_fundamentals_row(cik=noprice_cik)]).to_parquet(noprice_path, index=False)

    results = compute_metrics_for_tickers(
        pit_lake,
        tickers=["AAPL", "GHOST", "NOFUND", "NOPRICE"],
        as_of_date=RUN_DATE,
        cik_by_ticker={"AAPL": CIK, "NOFUND": other_cik, "NOPRICE": noprice_cik},
        show_progress=True,
    )

    assert [result.ticker for result in results] == ["AAPL"]


def test_select_pit_fundamentals_by_period_excludes_lookahead_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "cik": CIK,
                "fiscal_period_end": pd.Timestamp("2024-09-28"),
                "as_of_date": pd.Timestamp("2024-11-01"),
                "version_id": 1,
                "statement_variant": "quarterly",
            },
            {
                "cik": CIK,
                "fiscal_period_end": pd.Timestamp("2024-09-28"),
                "as_of_date": pd.Timestamp("2027-01-01"),
                "version_id": 2,
                "statement_variant": "quarterly",
            },
        ]
    )

    selected = _select_pit_fundamentals_by_period(frame, date(2026, 6, 18))

    assert len(selected) == 1
    assert selected.iloc[0]["version_id"] == 1


def test_load_pit_fundamentals_history_returns_multi_period_rows(pit_lake: Path) -> None:
    _write_fundamentals(
        pit_lake,
        period="2023Q4",
        row=_base_fundamentals_row(
            as_of_date=pd.Timestamp("2023-11-03"),
            fiscal_period_end=pd.Timestamp("2023-09-30"),
            statement_variant="quarterly",
            accounts_receivable=29_508_000_000,
        ),
    )
    _write_fundamentals(
        pit_lake,
        period="2024Q4",
        row=_base_fundamentals_row(
            statement_variant="quarterly",
            accounts_receivable=33_410_000_000,
        ),
    )

    history = load_pit_fundamentals_history(pit_lake, ticker="AAPL", as_of_date=RUN_DATE)

    assert len(history) == 2
    assert history.iloc[0]["fiscal_period_end"] == pd.Timestamp("2023-09-30")
    assert history.iloc[1]["accounts_receivable"] == 33_410_000_000


def test_load_pit_fundamentals_history_ignores_ttm_rows(pit_lake: Path) -> None:
    _write_fundamentals(
        pit_lake,
        period="2024Q4",
        row=_base_fundamentals_row(statement_variant="ttm"),
    )

    with pytest.raises(MetricsInputError, match="No PIT fundamentals history"):
        load_pit_fundamentals_history(pit_lake, ticker="AAPL", as_of_date=RUN_DATE)


def test_compute_metrics_for_tickers_loads_universe_when_cik_map_omitted(pit_lake: Path) -> None:
    results = compute_metrics_for_tickers(
        pit_lake,
        tickers=["AAPL"],
        as_of_date=RUN_DATE,
        show_progress=False,
    )

    assert len(results) == 1
    assert results[0].ticker == "AAPL"
