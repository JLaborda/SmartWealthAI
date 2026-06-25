"""Cross-sectional Magic Formula ranking and equal-weight portfolio construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.lake_paths import (
    curated_cheap_issues_path,
    curated_cheap_scores_path,
    curated_combined_ranking_path,
    curated_portfolio_path,
    curated_quality_issues_path,
    curated_quality_scores_path,
    curated_universe_path,
    pad_cik,
)
from smartwealthai.magic_formula_metrics import MetricsResult
from smartwealthai.pit_fundamentals import compute_metrics_for_tickers

DEFAULT_PORTFOLIO_SIZE = 30


@dataclass(frozen=True)
class RankInput:
    """One ticker eligible for a single-metric cross-sectional rank."""

    ticker: str
    metric_value: float
    market_cap: float


@dataclass(frozen=True)
class RankOutput:
    """Ranked ticker for one metric (lower rank = better)."""

    ticker: str
    metric_value: float
    market_cap: float
    rank: int


@dataclass
class PartitionedMetrics:
    """Metrics split into rankable names and per-factor review queues."""

    rankable: list[MetricsResult] = field(default_factory=list)
    quality_scorable: list[MetricsResult] = field(default_factory=list)
    cheap_scorable: list[MetricsResult] = field(default_factory=list)
    quality_review: list[MetricsResult] = field(default_factory=list)
    cheap_review: list[MetricsResult] = field(default_factory=list)


@dataclass(frozen=True)
class CombinedRankingRow:
    """One row in the combined Greenblatt ranking."""

    ticker: str
    cik: str
    ebit: float
    roc: float
    ey: float
    market_cap: float
    roc_rank: int
    ey_rank: int
    combined_rank: int
    formula_version: str
    as_of_date: date


@dataclass(frozen=True)
class PortfolioRow:
    """One equal-weight holding in the model portfolio."""

    ticker: str
    cik: str
    combined_rank: int
    weight: float
    market_cap: float


@dataclass
class ScoringResult:
    """Outcome of one universe scoring run."""

    run_date: date
    quality_path: Path
    cheap_path: Path
    combined_path: Path
    portfolio_path: Path
    quality_issues_path: Path
    cheap_issues_path: Path
    rankable_count: int
    portfolio_count: int


def assign_metric_ranks(
    rows: list[RankInput],
    *,
    higher_is_better: bool = True,
) -> list[RankOutput]:
    """Assign cross-sectional ranks with ascending market-cap tie-break."""
    if higher_is_better:
        ordered = sorted(rows, key=lambda row: (-row.metric_value, row.market_cap))
    else:
        ordered = sorted(rows, key=lambda row: (row.metric_value, row.market_cap))
    return [
        RankOutput(
            ticker=row.ticker,
            metric_value=row.metric_value,
            market_cap=row.market_cap,
            rank=index + 1,
        )
        for index, row in enumerate(ordered)
    ]


def is_quality_rankable(result: MetricsResult) -> bool:
    """Return True when ROC can enter the quality rank."""
    return (
        result.roc is not None
        and "invalid_roc_denominator" not in result.flags
        and "missing_inputs" not in result.flags
    )


def is_cheap_rankable(result: MetricsResult) -> bool:
    """Return True when EY can enter the cheapness rank."""
    return (
        result.ey is not None
        and "invalid_ev" not in result.flags
        and "negative_ebit" not in result.flags
        and "missing_inputs" not in result.flags
    )


def partition_metrics(results: list[MetricsResult]) -> PartitionedMetrics:
    """Split metrics into rankable tickers and review queues."""
    partitioned = PartitionedMetrics()
    for result in results:
        quality_ok = is_quality_rankable(result)
        cheap_ok = is_cheap_rankable(result)
        if quality_ok:
            partitioned.quality_scorable.append(result)
        else:
            partitioned.quality_review.append(result)
        if cheap_ok:
            partitioned.cheap_scorable.append(result)
        else:
            partitioned.cheap_review.append(result)
        if quality_ok and cheap_ok:
            partitioned.rankable.append(result)
    return partitioned


def build_combined_ranking(
    rankable: list[MetricsResult],
    roc_ranks: dict[str, int],
    ey_ranks: dict[str, int],
    *,
    cik_by_ticker: dict[str, str],
    as_of_date: date,
) -> list[CombinedRankingRow]:
    """Build combined rank rows sorted by combined rank then market cap."""
    rows: list[CombinedRankingRow] = []
    for result in rankable:
        assert result.roc is not None
        assert result.ey is not None
        assert result.market_cap is not None
        rows.append(
            CombinedRankingRow(
                ticker=result.ticker,
                cik=cik_by_ticker[result.ticker],
                ebit=result.ebit,  # type: ignore[arg-type]
                roc=result.roc,
                ey=result.ey,
                market_cap=result.market_cap,
                roc_rank=roc_ranks[result.ticker],
                ey_rank=ey_ranks[result.ticker],
                combined_rank=roc_ranks[result.ticker] + ey_ranks[result.ticker],
                formula_version=result.formula_version,
                as_of_date=as_of_date,
            )
        )
    return sorted(rows, key=lambda row: (row.combined_rank, row.market_cap))


def build_equal_weight_portfolio(
    ranking: list[CombinedRankingRow],
    *,
    top_n: int = DEFAULT_PORTFOLIO_SIZE,
) -> list[PortfolioRow]:
    """Select top names by combined rank with equal weights."""
    selected = ranking[:top_n]
    if not selected:
        return []
    weight = 1.0 / len(selected)
    return [
        PortfolioRow(
            ticker=row.ticker,
            cik=row.cik,
            combined_rank=row.combined_rank,
            weight=weight,
            market_cap=row.market_cap,
        )
        for row in selected
    ]


def _load_universe_tickers(data_dir: Path, *, run_date: date) -> pd.DataFrame:
    path = curated_universe_path(data_dir, run_date=run_date)
    if not path.exists():
        msg = f"No universe snapshot for run_date {run_date}: {path}"
        raise FileNotFoundError(msg)
    return pd.read_parquet(path)


def _metrics_to_quality_frame(
    results: list[MetricsResult],
    roc_ranks: dict[str, int],
    *,
    run_date: date,
    cik_by_ticker: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for result in results:
        if not is_quality_rankable(result):
            continue
        rows.append(
            {
                "run_date": run_date,
                "cik": cik_by_ticker[result.ticker],
                "ticker": result.ticker,
                "ebit": result.ebit,
                "nwc": result.nwc,
                "net_fixed_assets": result.net_fixed_assets,
                "roc": result.roc,
                "roc_rank": roc_ranks[result.ticker],
                "market_cap": result.market_cap,
                "formula_version": result.formula_version,
                "as_of_date": run_date,
            }
        )
    return pd.DataFrame(rows)


def _metrics_to_cheap_frame(
    results: list[MetricsResult],
    ey_ranks: dict[str, int],
    *,
    run_date: date,
    cik_by_ticker: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for result in results:
        if not is_cheap_rankable(result):
            continue
        rows.append(
            {
                "run_date": run_date,
                "cik": cik_by_ticker[result.ticker],
                "ticker": result.ticker,
                "ebit": result.ebit,
                "market_cap": result.market_cap,
                "total_debt": result.total_debt,
                "preferred_equity": result.preferred_equity,
                "minority_interest": result.minority_interest,
                "cash": result.cash,
                "ev": result.ev,
                "ey": result.ey,
                "ey_rank": ey_ranks[result.ticker],
                "formula_version": result.formula_version,
                "as_of_date": run_date,
            }
        )
    return pd.DataFrame(rows)


def _review_frame(
    results: list[MetricsResult],
    *,
    run_date: date,
    cik_by_ticker: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for result in results:
        rows.append(
            {
                "run_date": run_date,
                "cik": cik_by_ticker.get(result.ticker, ""),
                "ticker": result.ticker,
                "flags": ",".join(result.flags),
                "ebit": result.ebit,
                "roc": result.roc,
                "ey": result.ey,
            }
        )
    return pd.DataFrame(rows)


def _combined_frame(ranking: list[CombinedRankingRow], *, run_date: date) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "run_date": run_date,
                "cik": row.cik,
                "ticker": row.ticker,
                "ebit": row.ebit,
                "roc": row.roc,
                "ey": row.ey,
                "market_cap": row.market_cap,
                "roc_rank": row.roc_rank,
                "ey_rank": row.ey_rank,
                "combined_rank": row.combined_rank,
                "formula_version": row.formula_version,
                "as_of_date": row.as_of_date,
            }
            for row in ranking
        ]
    )


def _portfolio_frame(portfolio: list[PortfolioRow], *, run_date: date) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "run_date": run_date,
                "cik": row.cik,
                "ticker": row.ticker,
                "combined_rank": row.combined_rank,
                "weight": row.weight,
                "market_cap": row.market_cap,
            }
            for row in portfolio
        ]
    )


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def score_universe(
    data_dir: Path,
    *,
    run_date: date,
    portfolio_size: int = DEFAULT_PORTFOLIO_SIZE,
    show_progress: bool | None = None,
) -> ScoringResult:
    """Score every universe ticker, rank cross-sectionally, and write lake artifacts."""
    universe = _load_universe_tickers(data_dir, run_date=run_date)
    cik_by_ticker = {
        str(row["ticker"]).upper(): pad_cik(str(row["cik"])) for _, row in universe.iterrows()
    }
    tickers = [str(ticker).upper() for ticker in universe["ticker"]]

    metrics_results = compute_metrics_for_tickers(
        data_dir,
        tickers=tickers,
        as_of_date=run_date,
        cik_by_ticker=cik_by_ticker,
        show_progress=show_progress,
    )

    partitioned = partition_metrics(metrics_results)
    roc_ranked = assign_metric_ranks(
        [
            RankInput(
                ticker=result.ticker,
                metric_value=result.roc,  # type: ignore[arg-type]
                market_cap=result.market_cap,  # type: ignore[arg-type]
            )
            for result in partitioned.quality_scorable
        ]
    )
    ey_ranked = assign_metric_ranks(
        [
            RankInput(
                ticker=result.ticker,
                metric_value=result.ey,  # type: ignore[arg-type]
                market_cap=result.market_cap,  # type: ignore[arg-type]
            )
            for result in partitioned.cheap_scorable
        ]
    )
    roc_ranks = {row.ticker: row.rank for row in roc_ranked}
    ey_ranks = {row.ticker: row.rank for row in ey_ranked}

    combined = build_combined_ranking(
        partitioned.rankable,
        roc_ranks,
        ey_ranks,
        cik_by_ticker=cik_by_ticker,
        as_of_date=run_date,
    )
    portfolio = build_equal_weight_portfolio(combined, top_n=portfolio_size)

    quality_path = curated_quality_scores_path(data_dir, run_date=run_date)
    cheap_path = curated_cheap_scores_path(data_dir, run_date=run_date)
    combined_path = curated_combined_ranking_path(data_dir, run_date=run_date)
    portfolio_path = curated_portfolio_path(data_dir, run_date=run_date)
    quality_issues_path = curated_quality_issues_path(data_dir, run_date=run_date)
    cheap_issues_path = curated_cheap_issues_path(data_dir, run_date=run_date)

    _write_parquet(
        _metrics_to_quality_frame(
            metrics_results,
            roc_ranks,
            run_date=run_date,
            cik_by_ticker=cik_by_ticker,
        ),
        quality_path,
    )
    _write_parquet(
        _metrics_to_cheap_frame(
            metrics_results,
            ey_ranks,
            run_date=run_date,
            cik_by_ticker=cik_by_ticker,
        ),
        cheap_path,
    )
    _write_parquet(_combined_frame(combined, run_date=run_date), combined_path)
    _write_parquet(_portfolio_frame(portfolio, run_date=run_date), portfolio_path)
    _write_parquet(
        _review_frame(
            partitioned.quality_review,
            run_date=run_date,
            cik_by_ticker=cik_by_ticker,
        ),
        quality_issues_path,
    )
    _write_parquet(
        _review_frame(
            partitioned.cheap_review,
            run_date=run_date,
            cik_by_ticker=cik_by_ticker,
        ),
        cheap_issues_path,
    )

    return ScoringResult(
        run_date=run_date,
        quality_path=quality_path,
        cheap_path=cheap_path,
        combined_path=combined_path,
        portfolio_path=portfolio_path,
        quality_issues_path=quality_issues_path,
        cheap_issues_path=cheap_issues_path,
        rankable_count=len(partitioned.rankable),
        portfolio_count=len(portfolio),
    )
