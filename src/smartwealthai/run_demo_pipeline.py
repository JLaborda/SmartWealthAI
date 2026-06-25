"""CLI to run the June 30 demo slice pipeline end-to-end for one run date."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.compute_metrics import format_metrics_table
from smartwealthai.download_simfin import run_download
from smartwealthai.magic_formula_metrics import MetricsResult
from smartwealthai.normalize_simfin import resolve_normalize_tickers
from smartwealthai.pit_fundamentals import MetricsInputError, compute_metrics_for_ticker
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
    metrics_results: list[MetricsResult] = field(default_factory=list)
    metrics_errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        if not all(step.ok for step in self.steps):
            return False
        return not self.metrics_errors


def run_demo_pipeline(
    data_dir: Path,
    *,
    run_date: date,
    snapshot_date: date | None = None,
    tickers: tuple[str, ...] = (),
    refresh_days: int = 7,
    force: bool = False,
    skip_download: bool = False,
) -> PipelineResult:
    """Execute download → universe → normalize → prices → optional per-ticker metrics."""
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

    metrics_tickers = tuple(ticker.upper() for ticker in tickers)
    if not metrics_tickers:
        logger.info("[compute-metrics] skipped (pass --ticker to compute ROC/EY)")
        logger.info("Demo pipeline finished successfully")
        return result

    logger.info("[compute-metrics] starting — %d ticker(s)", len(metrics_tickers))
    started = time.monotonic()
    for ticker in metrics_tickers:
        logger.info("[compute-metrics] processing %s", ticker)
        try:
            metrics = compute_metrics_for_ticker(
                data_dir,
                ticker=ticker,
                as_of_date=run_date,
            )
        except MetricsInputError as exc:
            logger.warning("[compute-metrics] %s failed — %s", ticker, exc)
            result.metrics_errors.append((ticker, str(exc)))
            continue
        if "missing_inputs" in metrics.flags:
            logger.warning("[compute-metrics] %s failed — missing_inputs", ticker)
            result.metrics_errors.append((ticker, "missing_inputs"))
            continue
        logger.info(
            "[compute-metrics] %s ok — ROC=%s EY=%s",
            ticker,
            f"{metrics.roc:.4f}" if metrics.roc is not None else "n/a",
            f"{metrics.ey:.4f}" if metrics.ey is not None else "n/a",
        )
        result.metrics_results.append(metrics)

    elapsed = time.monotonic() - started
    metrics_ok = not result.metrics_errors
    logger.info(
        "[compute-metrics] finished in %.1fs — %d ok, %d failed",
        elapsed,
        len(result.metrics_results),
        len(result.metrics_errors),
    )
    result.steps.append(
        PipelineStepResult(
            name="compute-metrics",
            ok=metrics_ok,
            elapsed_s=elapsed,
            detail=(
                f"{len(result.metrics_results)} ok, {len(result.metrics_errors)} failed "
                f"of {len(metrics_tickers)} requested"
            ),
        )
    )
    if result.ok:
        logger.info("Demo pipeline finished successfully")
    else:
        logger.error("Demo pipeline finished with errors")
    return result


def format_pipeline_summary(result: PipelineResult) -> str:
    """Render a human-readable run summary."""
    lines = [f"Demo pipeline for {result.run_date}", ""]
    for step in result.steps:
        status = "OK" if step.ok else "FAIL"
        lines.append(f"  [{status}] {step.name} ({step.elapsed_s:.1f}s) — {step.detail}")
    if result.metrics_results:
        lines.append("")
        for metrics in result.metrics_results:
            lines.append(format_metrics_table(metrics))
            lines.append("")
    if result.metrics_errors:
        lines.append("Metrics failures:")
        for ticker, error in result.metrics_errors:
            lines.append(f"  {ticker}: {error}")
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
    help="Limit normalize scope to these tickers (intersect universe) and compute ROC/EY.",
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
    refresh_days: int,
    force: bool,
    skip_download: bool,
) -> None:
    """Run the demo slice: SimFin ingest, universe, normalize, prices, optional metrics."""
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
