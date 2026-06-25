"""Hermetic tests for demo universe construction (issue #58)."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from smartwealthai.lake_paths import simfin_bulk_path
from smartwealthai.simfin_industry_exclusions import REFERENCE_PATH
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
SNAPSHOT_DATE = date(2026, 6, 18)
RUN_DATE = date(2026, 6, 18)
BANK_INDUSTRY_ID = 104_002


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    """Copy fixture lake into an isolated temp directory."""
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    return tmp_path / "lake"


def _write_companies(lake: Path, rows: list[str]) -> None:
    header = "Ticker;SimFinId;Company Name;IndustryId;Market;CIK"
    path = simfin_bulk_path(
        lake,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=SNAPSHOT_DATE,
    )
    path.write_text(header + "\n" + "\n".join(rows) + "\n")


def _write_industries(lake: Path, rows: list[str]) -> None:
    header = "IndustryId;Industry;Sector"
    path = simfin_bulk_path(
        lake,
        dataset="industries",
        variant=None,
        market=None,
        as_of_date=SNAPSHOT_DATE,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "\n".join(rows) + "\n")


def _write_statement_index(lake: Path, *, dataset: str, rows: list[str]) -> None:
    header = (
        "Ticker;SimFinId;Report Date;Publish Date;Restated Date;"
        "Currency;Fiscal Year;Fiscal Period;Revenue"
    )
    path = simfin_bulk_path(
        lake,
        dataset=dataset,
        variant="ttm",
        market="us",
        as_of_date=SNAPSHOT_DATE,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "\n".join(rows) + "\n")


def test_build_universe_writes_included_ticker_from_companies(lake: Path) -> None:
    result = build_universe(lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)

    universe = pd.read_parquet(result.universe_path)
    assert list(universe.columns) == [
        "run_date",
        "ticker",
        "cik",
        "industry_id",
        "sector",
        "market_cap_usd",
    ]
    assert universe["run_date"].eq(RUN_DATE.isoformat()).all()
    assert "AAPL" in universe["ticker"].values
    assert universe.loc[universe["ticker"] == "AAPL", "sector"].iloc[0] == "Technology"
    assert result.universe_rows == 1
    assert result.exclusion_rows == 0


def test_excluded_industry_not_in_universe(lake: Path) -> None:
    _write_companies(
        lake,
        [
            "AAPL;111052;Apple Inc.;50;USA;0000320193",
            "JPM;111053;JPMorgan Chase & Co.;104002;USA;0000019617",
        ],
    )
    _write_industries(
        lake,
        [
            "50;Consumer Electronics;Technology",
            "104002;Banks;Financial Services",
        ],
    )

    result = build_universe(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        exclusions_path=REFERENCE_PATH,
    )

    universe = pd.read_parquet(result.universe_path)
    exclusions = pd.read_parquet(result.exclusions_path)

    assert "AAPL" in universe["ticker"].values
    assert "JPM" not in universe["ticker"].values
    jpm = exclusions.loc[exclusions["ticker"] == "JPM"].iloc[0]
    assert jpm["industry_id"] == BANK_INDUSTRY_ID
    assert jpm["exclusion_reason"] == "bank"
    assert result.universe_rows == 1
    assert result.exclusion_rows == 1


def test_bank_sanity_excludes_ticker_even_without_industry_match(lake: Path) -> None:
    _write_companies(
        lake,
        [
            "AAPL;111052;Apple Inc.;50;USA;0000320193",
            "SANBK;222001;Sanity Bank Corp.;50;USA;0001000001",
        ],
    )
    _write_industries(lake, ["50;Application Software;Technology"])
    _write_statement_index(
        lake,
        dataset="income-banks",
        rows=["SANBK;222001;2024-12-31;2025-02-01;;USD;2024;Q4;1000000"],
    )

    result = build_universe(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        exclusions_path=REFERENCE_PATH,
    )

    universe = pd.read_parquet(result.universe_path)
    exclusions = pd.read_parquet(result.exclusions_path)

    assert "SANBK" not in universe["ticker"].values
    sanity = exclusions.loc[exclusions["ticker"] == "SANBK"].iloc[0]
    assert sanity["exclusion_reason"] == "bank_sanity"


def test_insurance_sanity_excludes_ticker(lake: Path) -> None:
    _write_companies(
        lake,
        [
            "AAPL;111052;Apple Inc.;50;USA;0000320193",
            "SANIN;333001;Sanity Insurance Corp.;50;USA;0001000002",
        ],
    )
    _write_industries(lake, ["50;Application Software;Technology"])
    _write_statement_index(
        lake,
        dataset="income-insurance",
        rows=["SANIN;333001;2024-12-31;2025-02-01;;USD;2024;Q4;2000000"],
    )

    result = build_universe(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        exclusions_path=REFERENCE_PATH,
    )

    exclusions = pd.read_parquet(result.exclusions_path)
    sanity = exclusions.loc[exclusions["ticker"] == "SANIN"].iloc[0]
    assert sanity["exclusion_reason"] == "insurance_sanity"


def test_same_run_date_produces_identical_universe(lake: Path) -> None:
    kwargs = {
        "run_date": RUN_DATE,
        "snapshot_date": SNAPSHOT_DATE,
        "exclusions_path": REFERENCE_PATH,
    }
    first = build_universe(lake, **kwargs)
    second = build_universe(lake, **kwargs)

    assert first.universe_path.read_bytes() == second.universe_path.read_bytes()
    assert first.exclusions_path.read_bytes() == second.exclusions_path.read_bytes()


def test_cli_writes_universe_under_data_dir(lake: Path) -> None:
    from smartwealthai.build_universe import cli_run

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

    universe_path = (
        lake / "curated" / "universe" / f"run_date={RUN_DATE.isoformat()}" / "universe.parquet"
    )
    assert universe_path.exists()


def test_cli_defaults_snapshot_date_to_run_date(lake: Path) -> None:
    from smartwealthai.build_universe import cli_run

    assert cli_run(["--data-dir", str(lake), "--run-date", RUN_DATE.isoformat()]) == 0


def test_build_universe_module_main(lake: Path) -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "smartwealthai.build_universe",
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Built universe for" in result.stdout


def test_skips_blank_ticker_rows(lake: Path) -> None:
    _write_companies(
        lake,
        [
            "AAPL;111052;Apple Inc.;50;USA;0000320193",
            ";999999;Blank Ticker Inc.;50;USA;0000999999",
            "   ;888888;Whitespace Ticker Inc.;50;USA;0000888888",
        ],
    )

    result = build_universe(lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)

    universe = pd.read_parquet(result.universe_path)
    assert set(universe["ticker"]) == {"AAPL"}
    assert result.universe_rows == 1


def test_sector_from_exclusions_when_industries_missing(lake: Path, tmp_path: Path) -> None:
    exclusions = tmp_path / "exclusions.csv"
    exclusions.write_text(
        "industry_id,industry_name,sector,exclusion_reason\n104002,Banks,Financial Services,bank\n"
    )
    _write_companies(lake, ["JPM;111053;JPMorgan Chase & Co.;104002;USA;0000019617"])
    industries_path = simfin_bulk_path(
        lake,
        dataset="industries",
        variant=None,
        market=None,
        as_of_date=SNAPSHOT_DATE,
    )
    industries_path.unlink()

    result = build_universe(
        lake,
        run_date=RUN_DATE,
        snapshot_date=SNAPSHOT_DATE,
        exclusions_path=exclusions,
    )

    exclusions_df = pd.read_parquet(result.exclusions_path)
    jpm = exclusions_df.loc[exclusions_df["ticker"] == "JPM"].iloc[0]
    assert jpm["sector"] == "Financial Services"
    assert jpm["exclusion_reason"] == "bank"


def test_null_industry_id_included_with_null_sector(lake: Path) -> None:
    _write_companies(lake, ["NOIND;444001;No Industry Inc.;;USA;0001000003"])

    result = build_universe(lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)

    universe = pd.read_parquet(result.universe_path)
    row = universe.loc[universe["ticker"] == "NOIND"].iloc[0]
    assert pd.isna(row["industry_id"])
    assert row["sector"] is None or pd.isna(row["sector"])


def test_unknown_industry_id_has_null_sector(lake: Path) -> None:
    _write_companies(lake, ["UNK;555001;Unknown Industry Inc.;999999;USA;0001000004"])
    _write_industries(lake, ["50;Consumer Electronics;Technology"])

    result = build_universe(lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)

    universe = pd.read_parquet(result.universe_path)
    row = universe.loc[universe["ticker"] == "UNK"].iloc[0]
    assert row["industry_id"] == 999_999
    assert row["sector"] is None or pd.isna(row["sector"])


def test_missing_cik_allowed_in_universe(lake: Path) -> None:
    _write_companies(lake, ["NOCIK;666001;No CIK Inc.;50;USA;"])

    result = build_universe(lake, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)

    universe = pd.read_parquet(result.universe_path)
    row = universe.loc[universe["ticker"] == "NOCIK"].iloc[0]
    assert row["cik"] is None or pd.isna(row["cik"])
