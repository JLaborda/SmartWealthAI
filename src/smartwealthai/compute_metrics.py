"""CLI to compute Greenblatt ROC and EY for one ticker from the curated lake."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import click
from click.testing import CliRunner

from smartwealthai.magic_formula_metrics import MetricsResult
from smartwealthai.pit_fundamentals import MetricsInputError, compute_metrics_for_ticker


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--ticker",
    required=True,
    help="Ticker symbol (e.g. AAPL).",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data"),
    show_default=True,
    help="Data lake root.",
)
@click.option(
    "--as-of-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: datetime.now(tz=UTC).strftime("%Y-%m-%d"),
    show_default="today (UTC)",
    help="Decision date (PIT fundamentals and price snapshot).",
)
def main(ticker: str, data_dir: Path, as_of_date: datetime) -> None:
    """Compute ROC and EY for one ticker using curated fundamentals and prices."""
    decision_date = as_of_date.date()
    try:
        result = compute_metrics_for_ticker(
            data_dir,
            ticker=ticker.upper(),
            as_of_date=decision_date,
        )
    except MetricsInputError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc

    if "missing_inputs" in result.flags:
        click.echo("Required inputs are missing for metric computation.", err=True)
        raise SystemExit(1)

    click.echo(format_metrics_table(result))


def format_metrics_table(result: MetricsResult) -> str:
    """Render a human-readable breakdown of ROC/EY components."""
    lines = [
        f"Ticker: {result.ticker}",
        f"Formula version: {result.formula_version}",
        "",
        "Quality (ROC)",
        f"  EBIT:              {_fmt(result.ebit)}",
        f"  Current assets:    {_fmt(result.current_assets)}",
        f"  Cash:              {_fmt(result.cash)}",
        f"  Current liab.:     {_fmt(result.current_liabilities)}",
        f"  Short-term debt:   {_fmt(result.short_term_debt)}",
        f"  Net working cap.:  {_fmt(result.nwc)}",
        f"  Net fixed assets:  {_fmt(result.net_fixed_assets)}",
        f"  ROC denominator:   {_fmt(result.roc_denominator)}",
        f"  ROC:               {_fmt_ratio(result.roc)}",
        "",
        "Cheapness (EY)",
        f"  Shares outstanding:{_fmt(result.shares_outstanding)}",
        f"  Adj. close:        {_fmt(result.adj_close)}",
        f"  Market cap:        {_fmt(result.market_cap)}",
        f"  Long-term debt:    {_fmt(result.long_term_debt)}",
        f"  Short-term debt:   {_fmt(result.short_term_debt)}",
        f"  Total debt:        {_fmt(result.total_debt)}",
        f"  Preferred equity:  {_fmt(result.preferred_equity)}",
        f"  Minority interest: {_fmt(result.minority_interest)}",
        f"  Cash:              {_fmt(result.cash)}",
        f"  Enterprise value:  {_fmt(result.ev)}",
        f"  EY:                {_fmt_ratio(result.ey)}",
    ]
    if result.flags:
        lines.extend(["", f"Flags: {', '.join(result.flags)}"])
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f}"


def _fmt_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f} ({value * 100:.2f}%)"


def cli_run(argv: list[str] | None = None) -> int:
    """Invoke the CLI programmatically (e.g. in tests)."""
    runner = CliRunner()
    result = runner.invoke(main, argv or [], catch_exceptions=False)
    return result.exit_code


if __name__ == "__main__":
    main()
