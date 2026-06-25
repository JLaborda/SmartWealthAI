"""Hermetic tests for cross-sectional Magic Formula ranking (issue #60)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from smartwealthai.lake_paths import (
    curated_cheap_scores_path,
    curated_combined_ranking_path,
    curated_portfolio_path,
    curated_quality_scores_path,
    curated_universe_path,
)
from smartwealthai.magic_formula_metrics import build_metrics
from smartwealthai.magic_formula_ranking import (
    CombinedRankingRow,
    RankInput,
    _metrics_to_quality_frame,
    assign_metric_ranks,
    build_combined_ranking,
    build_equal_weight_portfolio,
    partition_metrics,
    score_universe,
)
from smartwealthai.normalize_simfin import cli_run as normalize_cli_run
from smartwealthai.pit_fundamentals import (
    MetricsInputError,
    compute_metrics_for_ticker,
    compute_metrics_for_tickers,
)
from smartwealthai.price_ingest import run_price_ingest
from smartwealthai.score_universe import cli_run as score_cli_run
from smartwealthai.score_universe import format_scoring_summary
from smartwealthai.score_universe import main as score_main
from smartwealthai.universe_builder import build_universe

FIXTURE_LAKE = Path("tests/fixtures/lake")
RUN_DATE = date(2026, 6, 18)
SNAPSHOT_DATE = date(2026, 6, 18)

# Synthetic fixture tickers (see tests/fixtures/lake/raw/simfin/).
MSFT_ROC = 200_000_000.0 / 120_000_000.0
MSFT_EY = 200_000_000.0 / 1_090_000_000.0
MSFT_MARKET_CAP = 20_000_000.0 * 50.0

FOO_ROC = 100_000_000.0 / 65_000_000.0
FOO_EY = 100_000_000.0 / 195_000_000.0
FOO_MARKET_CAP = 10_000_000.0 * 20.0

BAR_ROC = 50_000_000.0 / 45_000_000.0
BAR_EY = 50_000_000.0 / 155_000_000.0
BAR_MARKET_CAP = 5_000_000.0 * 30.0


@pytest.fixture
def lake(tmp_path: Path) -> Path:
    """Prepared lake with universe, curated fundamentals, and prices."""
    shutil.copytree(FIXTURE_LAKE, tmp_path / "lake")
    root = tmp_path / "lake"
    build_universe(root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    normalize_cli_run(
        [
            "--data-dir",
            str(root),
            "--snapshot-date",
            SNAPSHOT_DATE.isoformat(),
            "--universe-run-date",
            RUN_DATE.isoformat(),
        ]
    )
    run_price_ingest(data_dir=root, run_date=RUN_DATE, snapshot_date=SNAPSHOT_DATE)
    return root


def test_assign_metric_ranks_orders_by_metric_descending() -> None:
    rows = [
        RankInput(ticker="LOW", metric_value=0.10, market_cap=500.0),
        RankInput(ticker="MID", metric_value=0.20, market_cap=300.0),
        RankInput(ticker="HIGH", metric_value=0.30, market_cap=100.0),
    ]
    ranked = assign_metric_ranks(rows)

    assert [row.ticker for row in ranked] == ["HIGH", "MID", "LOW"]
    assert [row.rank for row in ranked] == [1, 2, 3]


def test_assign_metric_ranks_breaks_ties_by_ascending_market_cap() -> None:
    rows = [
        RankInput(ticker="BIG", metric_value=0.20, market_cap=1_000.0),
        RankInput(ticker="SMALL", metric_value=0.20, market_cap=100.0),
    ]
    ranked = assign_metric_ranks(rows)

    assert ranked[0].ticker == "SMALL"
    assert ranked[0].rank == 1
    assert ranked[1].ticker == "BIG"
    assert ranked[1].rank == 2


def test_assign_metric_ranks_orders_ascending_when_lower_is_better() -> None:
    rows = [
        RankInput(ticker="HIGH", metric_value=0.30, market_cap=100.0),
        RankInput(ticker="LOW", metric_value=0.10, market_cap=200.0),
    ]
    ranked = assign_metric_ranks(rows, higher_is_better=False)

    assert [row.ticker for row in ranked] == ["LOW", "HIGH"]
    assert [row.rank for row in ranked] == [1, 2]


def test_partition_metrics_excludes_invalid_and_negative_ebit_from_rankable() -> None:
    valid = build_metrics(
        ticker="OK",
        ebit=100.0,
        current_assets=200.0,
        current_liabilities=80.0,
        cash=20.0,
        short_term_debt=0.0,
        net_fixed_assets=100.0,
        shares_outstanding=10.0,
        adj_close=25.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )
    bad_roc = build_metrics(
        ticker="BAD_ROC",
        ebit=100.0,
        current_assets=10.0,
        current_liabilities=10.0,
        cash=10.0,
        short_term_debt=0.0,
        net_fixed_assets=0.0,
        shares_outstanding=1.0,
        adj_close=10.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )
    bad_ey = build_metrics(
        ticker="BAD_EY",
        ebit=-50.0,
        current_assets=200.0,
        current_liabilities=80.0,
        cash=20.0,
        short_term_debt=0.0,
        net_fixed_assets=100.0,
        shares_outstanding=10.0,
        adj_close=25.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )

    partitioned = partition_metrics([valid, bad_roc, bad_ey])

    assert [row.ticker for row in partitioned.rankable] == ["OK"]
    assert {row.ticker for row in partitioned.quality_review} == {"BAD_ROC"}
    assert {row.ticker for row in partitioned.cheap_review} == {"BAD_EY", "BAD_ROC"}


def test_build_combined_ranking_sums_ranks_and_orders_by_market_cap_tiebreak() -> None:
    rankable = [
        build_metrics(
            ticker="FOO",
            ebit=100.0,
            current_assets=50.0,
            current_liabilities=30.0,
            cash=10.0,
            short_term_debt=5.0,
            net_fixed_assets=50.0,
            shares_outstanding=10.0,
            adj_close=20.0,
            long_term_debt=0.0,
            preferred_equity=0.0,
            minority_interest=0.0,
        ),
        build_metrics(
            ticker="MSFT",
            ebit=200.0,
            current_assets=100.0,
            current_liabilities=50.0,
            cash=20.0,
            short_term_debt=10.0,
            net_fixed_assets=80.0,
            shares_outstanding=20.0,
            adj_close=50.0,
            long_term_debt=100.0,
            preferred_equity=0.0,
            minority_interest=0.0,
        ),
    ]
    roc_ranks = {"MSFT": 1, "FOO": 2}
    ey_ranks = {"FOO": 1, "MSFT": 2}
    cik_by_ticker = {"FOO": "0001000001", "MSFT": "0000789019"}

    combined = build_combined_ranking(
        rankable,
        roc_ranks,
        ey_ranks,
        cik_by_ticker=cik_by_ticker,
        as_of_date=RUN_DATE,
    )

    assert combined[0].ticker == "FOO"
    assert combined[0].combined_rank == 3
    assert combined[1].ticker == "MSFT"
    assert combined[1].combined_rank == 3


def test_build_equal_weight_portfolio_selects_top_n_with_equal_weights() -> None:
    ranking = [
        CombinedRankingRow(
            ticker="A",
            cik="0000000001",
            ebit=10.0,
            roc=0.2,
            ey=0.1,
            market_cap=100.0,
            roc_rank=1,
            ey_rank=1,
            combined_rank=2,
            formula_version="v1",
            as_of_date=RUN_DATE,
        ),
        CombinedRankingRow(
            ticker="B",
            cik="0000000002",
            ebit=8.0,
            roc=0.15,
            ey=0.08,
            market_cap=200.0,
            roc_rank=2,
            ey_rank=2,
            combined_rank=4,
            formula_version="v1",
            as_of_date=RUN_DATE,
        ),
        CombinedRankingRow(
            ticker="C",
            cik="0000000003",
            ebit=6.0,
            roc=0.10,
            ey=0.05,
            market_cap=300.0,
            roc_rank=3,
            ey_rank=3,
            combined_rank=6,
            formula_version="v1",
            as_of_date=RUN_DATE,
        ),
    ]

    portfolio = build_equal_weight_portfolio(ranking, top_n=2)

    assert len(portfolio) == 2
    assert [row.ticker for row in portfolio] == ["A", "B"]
    assert portfolio[0].weight == pytest.approx(0.5)
    assert portfolio[1].weight == pytest.approx(0.5)


def test_build_equal_weight_portfolio_returns_empty_for_empty_ranking() -> None:
    assert build_equal_weight_portfolio([]) == []


def test_metrics_to_quality_frame_skips_non_rankable_rows() -> None:
    valid = build_metrics(
        ticker="OK",
        ebit=100.0,
        current_assets=200.0,
        current_liabilities=80.0,
        cash=20.0,
        short_term_debt=0.0,
        net_fixed_assets=100.0,
        shares_outstanding=10.0,
        adj_close=25.0,
        long_term_debt=0.0,
        preferred_equity=0.0,
        minority_interest=0.0,
    )
    invalid = build_metrics(
        ticker="BAD",
        ebit=None,
        current_assets=None,
        current_liabilities=None,
        cash=None,
        short_term_debt=None,
        net_fixed_assets=None,
        shares_outstanding=None,
        adj_close=None,
        long_term_debt=None,
        preferred_equity=None,
        minority_interest=0.0,
    )

    frame = _metrics_to_quality_frame(
        [invalid, valid],
        {"OK": 1},
        run_date=RUN_DATE,
        cik_by_ticker={"OK": "0000000001", "BAD": "0000000002"},
    )

    assert list(frame["ticker"]) == ["OK"]


def test_score_universe_raises_when_universe_snapshot_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No universe snapshot"):
        score_universe(tmp_path, run_date=RUN_DATE)


def test_score_universe_writes_all_artifacts(lake: Path) -> None:
    result = score_universe(lake, run_date=RUN_DATE, portfolio_size=3)

    assert result.rankable_count == 4
    assert result.portfolio_count == 3
    assert result.quality_path.exists()
    assert result.cheap_path.exists()
    assert result.combined_path.exists()
    assert result.portfolio_path.exists()
    assert result.quality_issues_path.exists()
    assert result.cheap_issues_path.exists()

    quality = pd.read_parquet(result.quality_path)
    cheap = pd.read_parquet(result.cheap_path)
    combined = pd.read_parquet(result.combined_path)
    portfolio = pd.read_parquet(result.portfolio_path)
    cheap_issues = pd.read_parquet(result.cheap_issues_path)

    assert "roc_rank" in quality.columns
    assert "ey_rank" in cheap.columns
    assert "combined_rank" in combined.columns
    assert list(portfolio.columns) == [
        "run_date",
        "cik",
        "ticker",
        "combined_rank",
        "weight",
        "market_cap",
    ]
    assert portfolio["weight"].tolist() == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    assert "LOST" in cheap_issues["ticker"].values


def test_score_universe_fixture_ranking_order_is_deterministic(lake: Path) -> None:
    score_universe(lake, run_date=RUN_DATE, portfolio_size=3)
    combined = pd.read_parquet(curated_combined_ranking_path(lake, run_date=RUN_DATE))
    portfolio = pd.read_parquet(curated_portfolio_path(lake, run_date=RUN_DATE))

    # FOO has best combined rank (4); MSFT and AAPL tie at 5 (MSFT smaller mcap first).
    assert combined.iloc[0]["ticker"] == "FOO"
    assert combined.iloc[0]["combined_rank"] == 4
    assert list(portfolio["ticker"]) == ["FOO", "MSFT", "AAPL"]


def test_score_universe_fixture_metric_values_match_synthetic_inputs(lake: Path) -> None:
    score_universe(lake, run_date=RUN_DATE, portfolio_size=30)
    quality = pd.read_parquet(curated_quality_scores_path(lake, run_date=RUN_DATE))
    cheap = pd.read_parquet(curated_cheap_scores_path(lake, run_date=RUN_DATE))

    msft_quality = quality.loc[quality["ticker"] == "MSFT"].iloc[0]
    foo_cheap = cheap.loc[cheap["ticker"] == "FOO"].iloc[0]

    assert msft_quality["roc"] == pytest.approx(MSFT_ROC)
    assert foo_cheap["ey"] == pytest.approx(FOO_EY)
    assert msft_quality["market_cap"] == pytest.approx(MSFT_MARKET_CAP)
    assert foo_cheap["market_cap"] == pytest.approx(FOO_MARKET_CAP)


def test_cli_score_universe_succeeds_on_fixture_lake(lake: Path) -> None:
    exit_code = score_cli_run(
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--portfolio-size",
            "3",
        ]
    )
    assert exit_code == 0


def test_score_universe_entry_point_registered() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "smartwealthai.score_universe", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--run-date" in result.stdout
    assert "--progress" in result.stdout


def _universe_tickers(lake: Path) -> list[str]:
    universe = pd.read_parquet(curated_universe_path(lake, run_date=RUN_DATE))
    return [str(ticker).upper() for ticker in universe["ticker"]]


def _metrics_result_key(result: object) -> tuple:
    from smartwealthai.magic_formula_metrics import MetricsResult

    assert isinstance(result, MetricsResult)
    return (
        result.ticker,
        result.roc,
        result.ey,
        result.market_cap,
        tuple(result.flags),
        result.ebit,
    )


def test_bulk_metrics_match_per_ticker_on_fixture_lake(lake: Path) -> None:
    tickers = _universe_tickers(lake)
    per_ticker = []
    for ticker in tickers:
        try:
            per_ticker.append(compute_metrics_for_ticker(lake, ticker=ticker, as_of_date=RUN_DATE))
        except MetricsInputError:
            continue

    bulk = compute_metrics_for_tickers(
        lake, tickers=tickers, as_of_date=RUN_DATE, show_progress=False
    )

    per_ticker_by_name = {_metrics_result_key(result): result for result in per_ticker}
    bulk_by_name = {_metrics_result_key(result): result for result in bulk}
    assert per_ticker_by_name == bulk_by_name


def test_score_universe_fixture_completes_under_5s(lake: Path) -> None:
    started = time.monotonic()
    score_universe(lake, run_date=RUN_DATE, portfolio_size=3, show_progress=False)
    assert time.monotonic() - started < 5.0


def test_cli_progress_and_quiet_mutually_exclusive(lake: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        score_main,
        [
            "--data-dir",
            str(lake),
            "--run-date",
            RUN_DATE.isoformat(),
            "--progress",
            "--quiet",
        ],
    )
    assert result.exit_code != 0
    assert "only one of --progress or --quiet" in result.output


def test_format_scoring_summary_raises_for_non_scoring_result() -> None:
    with pytest.raises(TypeError, match="expected ScoringResult"):
        format_scoring_summary(object())


def test_cli_score_universe_fails_when_universe_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        score_main,
        [
            "--data-dir",
            str(tmp_path),
            "--run-date",
            RUN_DATE.isoformat(),
        ],
    )

    assert result.exit_code == 1
    assert "No universe snapshot" in result.output
