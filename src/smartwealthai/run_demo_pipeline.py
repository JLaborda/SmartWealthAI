"""CLI to run the June 30 demo slice pipeline end-to-end for one run date."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.download_simfin import run_download
from smartwealthai.magic_formula_ranking import ScoringResult, score_universe
from smartwealthai.normalize_simfin import resolve_normalize_tickers
from smartwealthai.price_ingest import run_price_ingest
from smartwealthai.simfin_normalizer import normalize_simfin
from smartwealthai.universe_builder import build_universe

logger = logging.getLogger(__name__)


@dataclass
class PipelineStepResult:
    """Outcome of one pipeline stage."""

    name: str
    ok: bool
    elapsed_s: float
    detail: str


@dataclass
class PipelineResult:
    """Summary of a full demo pipeline run."""

    run_date: date
    steps: list[PipelineStepResult] = field(default_factory=list)
    scoring: ScoringResult | None = None

    @property
    def ok(self) -> bool:
        return all(step.ok for step in self.steps)


def run_demo_pipeline(
    data_dir: Path,
    *,
    run_date: date,
    snapshot_date: date | None = None,
    tickers: tuple[str, ...] = (),
    refresh_days: int = 7,
    force: bool = False,
    skip_download: bool = False,
    portfolio_size: int = 30,
    skip_mlflow: bool = False,
) -> PipelineResult:
    """Execute download → universe → normalize → prices → score-universe."""
    snapshot = snapshot_date or run_date
    result = PipelineResult(run_date=run_date)
    logger.info(
        "Demo pipeline starting (run_date=%s, snapshot=%s, data_dir=%s)",
        run_date,
        snapshot,
        data_dir,
    )

    if not skip_download:
        logger.info("[download-simfin] starting (force=%s, refresh_days=%d)", force, refresh_days)
        started = time.monotonic()
        exit_code = run_download(
            data_dir=data_dir,
            as_of_date=snapshot,
            refresh_days=refresh_days,
            force=force,
        )
        elapsed = time.monotonic() - started
        logger.info("[download-simfin] finished in %.1fs — exit %d", elapsed, exit_code)
        result.steps.append(
            PipelineStepResult(
                name="download-simfin",
                ok=exit_code == 0,
                elapsed_s=elapsed,
                detail=f"exit {exit_code}",
            )
        )
        if exit_code != 0:
            logger.error("[download-simfin] failed — aborting pipeline")
            return result
    else:
        logger.info("[download-simfin] skipped (--skip-download)")

    logger.info("[build-universe] starting")
    started = time.monotonic()
    universe = build_universe(data_dir, run_date=run_date, snapshot_date=snapshot)
    elapsed = time.monotonic() - started
    logger.info(
        "[build-universe] finished in %.1fs — %d included, %d excluded",
        elapsed,
        universe.universe_rows,
        universe.exclusion_rows,
    )
    result.steps.append(
        PipelineStepResult(
            name="build-universe",
            ok=True,
            elapsed_s=elapsed,
            detail=f"{universe.universe_rows} included, {universe.exclusion_rows} excluded",
        )
    )

    logger.info("[normalize-simfin] starting")
    started = time.monotonic()
    ticker_set = resolve_normalize_tickers(
        data_dir,
        universe_run_date=run_date,
        explicit_tickers=tickers,
    )
    logger.info("[normalize-simfin] scope: %d ticker(s)", len(ticker_set))
    normalize = normalize_simfin(
        data_dir,
        snapshot_date=snapshot,
        tickers=ticker_set,
        run_date=run_date,
        show_progress=None,
    )
    elapsed = time.monotonic() - started
    logger.info(
        "[normalize-simfin] finished in %.1fs — %d curated, %d issues",
        elapsed,
        normalize.written_rows,
        normalize.issue_rows,
    )
    result.steps.append(
        PipelineStepResult(
            name="normalize-simfin",
            ok=True,
            elapsed_s=elapsed,
            detail=(
                f"{len(ticker_set)} tickers, "
                f"{normalize.written_rows} curated, {normalize.issue_rows} issues"
            ),
        )
    )

    logger.info("[download-prices] starting (force=%s)", force)
    started = time.monotonic()
    try:
        prices = run_price_ingest(
            data_dir=data_dir,
            run_date=run_date,
            snapshot_date=snapshot,
            force=force,
        )
    except FileNotFoundError as exc:
        elapsed = time.monotonic() - started
        logger.error("[download-prices] failed in %.1fs — %s", elapsed, exc)
        result.steps.append(
            PipelineStepResult(
                name="download-prices",
                ok=False,
                elapsed_s=elapsed,
                detail=str(exc),
            )
        )
        return result

    elapsed = time.monotonic() - started
    prices_ok = prices.run_skipped or prices.included > 0
    prices_detail = (
        "skipped (existing snapshot)"
        if prices.run_skipped
        else f"{prices.included} priced, {len(prices.missing_tickers)} missing"
    )
    log_fn = logger.info if prices_ok else logger.error
    log_fn("[download-prices] finished in %.1fs — %s", elapsed, prices_detail)
    result.steps.append(
        PipelineStepResult(
            name="download-prices",
            ok=prices_ok,
            elapsed_s=elapsed,
            detail=prices_detail,
        )
    )
    if not prices_ok:
        logger.error("[download-prices] failed — aborting pipeline")
        return result

    logger.info("[score-universe] starting (portfolio_size=%d)", portfolio_size)
    started = time.monotonic()
    scoring = score_universe(
        data_dir,
        run_date=run_date,
        portfolio_size=portfolio_size,
        skip_mlflow=skip_mlflow,
    )
    elapsed = time.monotonic() - started
    result.scoring = scoring
    scoring_detail = (
        f"{scoring.rankable_count} rankable, {scoring.portfolio_count} in portfolio"
    )
    logger.info("[score-universe] finished in %.1fs — %s", elapsed, scoring_detail)
    result.steps.append(
        PipelineStepResult(
            name="score-universe",
            ok=True,
            elapsed_s=elapsed,
            detail=scoring_detail,
        )
    )
    logger.info("Demo pipeline finished successfully")
    return result


def format_pipeline_summary(result: PipelineResult) -> str:
    """Render a human-readable run summary."""
    lines = [f"Demo pipeline for {result.run_date}", ""]
    for step in result.steps:
        status = "OK" if step.ok else "FAIL"
        lines.append(f"  [{status}] {step.name} ({step.elapsed_s:.1f}s) — {step.detail}")
    if result.scoring is not None:
        lines.extend(
            [
                "",
                "Artifacts:",
                f"  quality:   {result.scoring.quality_path}",
                f"  cheap:     {result.scoring.cheap_path}",
                f"  combined:  {result.scoring.combined_path}",
                f"  portfolio: {result.scoring.portfolio_path}",
            ]
        )
        if result.scoring.mlflow_run_id:
            lines.append(f"  MLflow run id: {result.scoring.mlflow_run_id}")
    return "\n".join(lines).rstrip()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data"),
    show_default=True,
    help="Data lake root.",
)
@click.option(
    "--run-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Pipeline decision date (universe, prices, PIT metrics).",
)
@click.option(
    "--snapshot-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Raw SimFin bulk partition date (defaults to run-date).",
)
@click.option(
    "--ticker",
    "tickers",
    multiple=True,
    help="Limit normalize scope to these tickers (intersect universe).",
)
@click.option(
    "--portfolio-size",
    type=int,
    default=30,
    show_default=True,
    help="Top-N equal-weight holdings in the model portfolio.",
)
@click.option(
    "--skip-mlflow",
    is_flag=True,
    help="Skip MLflow run logging (useful for hermetic tests).",
)
@click.option(
    "--refresh-days",
    type=int,
    default=7,
    show_default=True,
    help="Skip SimFin download when raw lake copies are fresher than this.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-download SimFin bulk and rebuild curated prices.",
)
@click.option(
    "--skip-download",
    is_flag=True,
    help="Skip SimFin bulk download (use existing raw lake).",
)
def main(
    data_dir: Path,
    run_date: datetime,
    snapshot_date: datetime | None,
    tickers: tuple[str, ...],
    portfolio_size: int,
    skip_mlflow: bool,
    refresh_days: int,
    force: bool,
    skip_download: bool,
) -> None:
    """Run the demo slice: SimFin ingest, universe, normalize, prices, score-universe."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    decision_date = run_date.date()
    snapshot = snapshot_date.date() if snapshot_date is not None else decision_date

    try:
        result = run_demo_pipeline(
            data_dir,
            run_date=decision_date,
            snapshot_date=snapshot,
            tickers=tickers,
            refresh_days=refresh_days,
            force=force,
            skip_download=skip_download,
            portfolio_size=portfolio_size,
            skip_mlflow=skip_mlflow,
        )
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc

    click.echo(format_pipeline_summary(result))
    if not result.ok:
        raise SystemExit(1)


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [])
    return result.exit_code


if __name__ == "__main__":
    main()
