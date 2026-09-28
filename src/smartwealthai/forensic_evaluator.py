"""Forensic evaluator orchestrator for the permanent-loss filter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from smartwealthai.accrual_scores import (
    AccrualMetrics,
    build_comboaccrual_forensic_scores,
    compute_accrual_metrics,
)
from smartwealthai.beneish_score import compute_beneish_m_score
from smartwealthai.distress_rules import (
    EXCLUSION_COLUMNS,
    RuleEvaluation,
    distress_inputs_from_row,
    evaluate_distress_rules,
    evaluate_fraud_rules,
)
from smartwealthai.forensic_percentile_gate import ForensicScore, apply_bottom_percentile_gate
from smartwealthai.lake_paths import (
    curated_permanent_loss_exclusions_path,
    curated_permanent_loss_issues_path,
    curated_prices_snapshot_path,
    curated_universe_path,
    pad_cik,
)
from smartwealthai.permanent_loss_config import (
    load_accrual_config,
    load_beneish_config,
    load_comboaccrual_gate_config,
    load_distress_rules_config,
    load_forensic_gate_config,
)
from smartwealthai.pit_fundamentals import (
    _fundamentals_paths_for_ciks,
    _read_fundamentals_partition_all,
    _select_pit_fundamentals,
    _select_pit_fundamentals_by_period,
)

REVIEW_COLUMNS: tuple[str, ...] = ("run_date", "ticker", "cik", "reason", "rule_id")


@dataclass
class ForensicEvaluatorResult:
    """Outcome of one forensic evaluator run."""

    exclusions_path: Path
    issues_path: Path | None
    evaluated_count: int
    exclusion_count: int
    review_count: int


def _market_cap(fundamentals: pd.Series, price_row: pd.Series | None) -> float | None:
    shares = fundamentals.get("shares_outstanding")
    adj_close = price_row.get("adj_close") if price_row is not None else None
    if shares is None or adj_close is None:
        return price_row.get("market_cap_usd") if price_row is not None else None
    try:
        if pd.isna(shares) or pd.isna(adj_close):
            return None
    except TypeError:
        pass
    return float(shares) * float(adj_close)


def _load_prices(data_dir: Path, *, run_date: date) -> dict[str, pd.Series]:
    path = curated_prices_snapshot_path(data_dir, run_date=run_date)
    if not path.exists():
        return {}
    frame = pd.read_parquet(path)
    return {str(row["ticker"]).upper(): row for _, row in frame.iterrows()}


def _load_latest_fundamentals(
    data_dir: Path,
    *,
    ciks: set[str],
    as_of_date: date,
) -> dict[str, pd.Series]:
    paths = _fundamentals_paths_for_ciks(data_dir, ciks)
    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = _read_fundamentals_partition_all(path)
        if frame is not None:
            frames.append(frame)
    if not frames:
        return {}
    selected = _select_pit_fundamentals(pd.concat(frames, ignore_index=True), as_of_date)
    return {pad_cik(str(row["cik"])): row for _, row in selected.iterrows()}


def _load_fundamentals_history(
    data_dir: Path,
    *,
    cik: str,
    as_of_date: date,
) -> pd.DataFrame:
    paths = _fundamentals_paths_for_ciks(data_dir, {cik})
    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = _read_fundamentals_partition_all(path)
        if frame is not None:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    history = pd.concat(frames, ignore_index=True)
    if "statement_variant" in history.columns:
        history = history.loc[history["statement_variant"].isin(("annual", "quarterly"))]
    selected = _select_pit_fundamentals_by_period(history, as_of_date)
    return selected.sort_values("fiscal_period_end").reset_index(drop=True)


def _prior_fundamentals_row(history: pd.DataFrame) -> pd.Series | None:
    if len(history) < 2:
        return None
    return history.sort_values("fiscal_period_end").iloc[-2]


def _evaluation_to_exclusion_row(
    *,
    cik: str,
    ticker: str,
    evaluation: RuleEvaluation,
    as_of_date: date,
) -> dict[str, object]:
    return {
        "cik": pad_cik(cik),
        "ticker": ticker,
        "subfilter": evaluation.subfilter,
        "rule_id": evaluation.rule_id,
        "rule_version": evaluation.rule_version,
        "triggered_value": evaluation.triggered_value,
        "threshold": evaluation.threshold,
        "as_of_date": as_of_date.isoformat(),
        "explanation": evaluation.explanation,
    }


def _percentile_to_exclusion_row(
    *,
    exclusion: object,
    as_of_date: date,
) -> dict[str, object]:
    return {
        "cik": pad_cik(exclusion.cik),
        "ticker": exclusion.ticker,
        "subfilter": "forensic_percentile",
        "rule_id": exclusion.rule_id,
        "rule_version": exclusion.rule_version,
        "triggered_value": exclusion.score,
        "threshold": exclusion.threshold_percentile,
        "as_of_date": as_of_date.isoformat(),
        "explanation": exclusion.explanation,
    }


def run_forensic_evaluator(
    data_dir: Path,
    *,
    run_date: date,
    distress_config: dict | None = None,
    beneish_config: dict | None = None,
    accrual_config: dict | None = None,
    gate_config: dict | None = None,
    comboaccrual_gate_config: dict | None = None,
) -> ForensicEvaluatorResult:
    """Evaluate forensic rules for the universe on ``run_date`` and write exclusions."""
    distress_cfg = distress_config or load_distress_rules_config()
    beneish_cfg = beneish_config or load_beneish_config()
    accrual_cfg = accrual_config or load_accrual_config()
    gate_cfg = gate_config or load_forensic_gate_config()
    combo_cfg = comboaccrual_gate_config or load_comboaccrual_gate_config()

    universe_path = curated_universe_path(data_dir, run_date=run_date)
    if not universe_path.exists():
        msg = f"No universe snapshot for run_date {run_date}: {universe_path}"
        raise FileNotFoundError(msg)

    universe = pd.read_parquet(universe_path)
    prices = _load_prices(data_dir, run_date=run_date)
    ciks = {pad_cik(str(row["cik"])) for _, row in universe.iterrows() if pd.notna(row["cik"])}
    fundamentals_by_cik = _load_latest_fundamentals(data_dir, ciks=ciks, as_of_date=run_date)

    exclusion_rows: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    beneish_candidates: list[ForensicScore] = []
    accrual_candidates: list[tuple[str, str, AccrualMetrics, float]] = []
    hard_excluded: set[str] = set()

    for _, row in universe.iterrows():
        ticker = str(row["ticker"]).upper()
        if pd.isna(row["cik"]):
            review_rows.append(
                {
                    "run_date": run_date.isoformat(),
                    "ticker": ticker,
                    "cik": None,
                    "reason": "missing_cik",
                    "rule_id": None,
                }
            )
            continue

        cik = pad_cik(str(row["cik"]))
        fundamentals = fundamentals_by_cik.get(cik)
        if fundamentals is None:
            review_rows.append(
                {
                    "run_date": run_date.isoformat(),
                    "ticker": ticker,
                    "cik": cik,
                    "reason": "missing_fundamentals",
                    "rule_id": None,
                }
            )
            continue

        price_row = prices.get(ticker)
        listing_status = str(price_row.get("listing_status")) if price_row is not None else None
        delisting_reason = str(price_row.get("delisting_reason")) if price_row is not None else None
        if price_row is not None and pd.isna(price_row.get("listing_status")):
            listing_status = None
        if price_row is not None and pd.isna(price_row.get("delisting_reason")):
            delisting_reason = None

        inputs = distress_inputs_from_row(
            fundamentals,
            market_cap=_market_cap(fundamentals, price_row),
            listing_status=listing_status,
            delisting_reason=delisting_reason,
        )
        evaluations = evaluate_distress_rules(inputs, config=distress_cfg) + evaluate_fraud_rules()

        excluded_here = False
        for evaluation in evaluations:
            if evaluation.status == "exclude":
                exclusion_rows.append(
                    _evaluation_to_exclusion_row(
                        cik=cik,
                        ticker=ticker,
                        evaluation=evaluation,
                        as_of_date=run_date,
                    )
                )
                excluded_here = True
            elif evaluation.status == "unavailable":
                review_rows.append(
                    {
                        "run_date": run_date.isoformat(),
                        "ticker": ticker,
                        "cik": cik,
                        "reason": evaluation.explanation,
                        "rule_id": evaluation.rule_id,
                    }
                )

        if excluded_here:
            hard_excluded.add(ticker)
            continue

        history = _load_fundamentals_history(data_dir, cik=cik, as_of_date=run_date)
        prior_row = _prior_fundamentals_row(history)
        market_cap = _market_cap(fundamentals, price_row) or 0.0

        accrual = compute_accrual_metrics(
            fundamentals,
            prior_row=prior_row,
            config=accrual_cfg,
        )
        if accrual.sta is None or accrual.snoa is None:
            if accrual.missing_fields:
                review_rows.append(
                    {
                        "run_date": run_date.isoformat(),
                        "ticker": ticker,
                        "cik": cik,
                        "reason": f"missing accrual inputs: {','.join(accrual.missing_fields)}",
                        "rule_id": "FRD_COMBOACCRUAL",
                    }
                )
        else:
            accrual_candidates.append((ticker, cik, accrual, market_cap))

        beneish = compute_beneish_m_score(history, config=beneish_cfg)
        if beneish.m_score is None:
            if beneish.missing_fields:
                review_rows.append(
                    {
                        "run_date": run_date.isoformat(),
                        "ticker": ticker,
                        "cik": cik,
                        "reason": f"missing beneish inputs: {','.join(beneish.missing_fields)}",
                        "rule_id": "FRD_BENEISH",
                    }
                )
            continue

        beneish_candidates.append(
            ForensicScore(
                ticker=ticker,
                cik=cik,
                model="beneish",
                score=beneish.m_score,
                rule_version=beneish.rule_version,
                market_cap=market_cap,
            )
        )

    for percentile_exclusion in apply_bottom_percentile_gate(beneish_candidates, config=gate_cfg):
        if percentile_exclusion.ticker in hard_excluded:
            continue
        exclusion_rows.append(
            _percentile_to_exclusion_row(exclusion=percentile_exclusion, as_of_date=run_date)
        )

    combo_scores = build_comboaccrual_forensic_scores(accrual_candidates)
    for percentile_exclusion in apply_bottom_percentile_gate(combo_scores, config=combo_cfg):
        if percentile_exclusion.ticker in hard_excluded:
            continue
        exclusion_rows.append(
            _percentile_to_exclusion_row(exclusion=percentile_exclusion, as_of_date=run_date)
        )

    exclusions_out = curated_permanent_loss_exclusions_path(data_dir, run_date=run_date)
    exclusions_out.parent.mkdir(parents=True, exist_ok=True)
    exclusions_df = pd.DataFrame(exclusion_rows, columns=list(EXCLUSION_COLUMNS))
    exclusions_df.to_parquet(exclusions_out, index=False)

    issues_out: Path | None = None
    if review_rows:
        issues_out = curated_permanent_loss_issues_path(data_dir, run_date=run_date)
        issues_out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(review_rows, columns=list(REVIEW_COLUMNS)).to_parquet(issues_out, index=False)

    return ForensicEvaluatorResult(
        exclusions_path=exclusions_out,
        issues_path=issues_out,
        evaluated_count=len(universe),
        exclusion_count=len(exclusions_df),
        review_count=len(review_rows),
    )
