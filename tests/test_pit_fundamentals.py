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
    _optional_float,
    compute_metrics_for_ticker,
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
        "version_id": 1,
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
