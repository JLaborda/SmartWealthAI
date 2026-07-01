"""SimFin bulk CSV → curated point-in-time fundamentals parquet."""

from __future__ import annotations

import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import click
import pandas as pd

from smartwealthai.lake_paths import (
    curated_fundamentals_path,
    curated_issues_path,
    fiscal_period_label,
    is_valid_cik,
    is_valid_fiscal_period,
    pad_cik,
    simfin_bulk_path,
)

DEFAULT_MAPPING_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "fundamentals" / "simfin_mapping_v1.yaml"
)

CANONICAL_VALUE_FIELDS: tuple[str, ...] = (
    "ebit",
    "revenue",
    "net_income",
    "current_assets",
    "current_liabilities",
    "cash",
    "short_term_debt",
    "ppe_net",
    "long_term_debt",
    "preferred_equity",
    "minority_interest",
    "total_assets",
    "total_liabilities",
    "shares_outstanding",
    "accounts_receivable",
    "cost_of_revenue",
    "depreciation_amortization",
    "sga_expense",
    "operating_cash_flow",
)

DATE_COLUMNS = ("Report Date", "Publish Date", "Restated Date")

# ponytail: I/O-bound cap; raise if profiling shows disk saturation
_WRITE_WORKERS = min(8, (os.cpu_count() or 4) + 2)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatementBundle:
    """One income/balance/cashflow variant group for normalization."""

    income_variant: str
    balance_variant: str
    cashflow_variant: str | None
    enforce_qv_fields: bool


STATEMENT_BUNDLES: tuple[StatementBundle, ...] = (
    StatementBundle("ttm", "quarterly", None, enforce_qv_fields=False),
    StatementBundle("annual", "annual", "annual", enforce_qv_fields=True),
    StatementBundle("quarterly", "quarterly", "quarterly", enforce_qv_fields=True),
)


@dataclass
class NormalizeResult:
    """Outcome counters for one normalizer run."""

    written_rows: int = 0
    issue_rows: int = 0


def load_simfin_mapping(path: Path = DEFAULT_MAPPING_PATH) -> dict:
    """Load the SimFin → canonical column mapping from YAML."""
    return _load_mapping_yaml(path)


def normalize_simfin(
    data_dir: Path,
    *,
    snapshot_date: date,
    mapping_path: Path = DEFAULT_MAPPING_PATH,
    tickers: set[str] | None = None,
    run_date: date | None = None,
    show_progress: bool | None = None,
) -> NormalizeResult:
    """Transform raw SimFin bulk CSVs into curated fundamentals parquet."""
    progress_enabled = _resolve_show_progress(show_progress)
    mapping = load_simfin_mapping(mapping_path)
    companies_path = simfin_bulk_path(
        data_dir,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=snapshot_date,
    )
    companies = pd.read_csv(companies_path, sep=";", dtype={"CIK": "string"})
    company_lookup = companies.set_index(mapping["meta"]["ticker"], drop=False)

    curated_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []
    effective_run_date = run_date or snapshot_date

    for bundle in STATEMENT_BUNDLES:
        bundle_rows, bundle_issues = _normalize_statement_bundle(
            data_dir,
            snapshot_date=snapshot_date,
            bundle=bundle,
            mapping=mapping,
            company_lookup=company_lookup,
            tickers=tickers,
            show_progress=progress_enabled,
        )
        curated_rows.extend(bundle_rows)
        issue_rows.extend(bundle_issues)

    result = NormalizeResult()
    result.written_rows = _write_curated_fundamentals(
        data_dir,
        curated_rows,
        show_progress=progress_enabled,
    )

    if issue_rows:
        issues_path = curated_issues_path(data_dir, run_date=effective_run_date)
        issues_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(issue_rows).to_parquet(issues_path, index=False)
        result.issue_rows = len(issue_rows)

    return result


def _normalize_statement_bundle(
    data_dir: Path,
    *,
    snapshot_date: date,
    bundle: StatementBundle,
    mapping: dict,
    company_lookup: pd.DataFrame,
    tickers: set[str] | None,
    show_progress: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    paths = _raw_paths_for_bundle(data_dir, snapshot_date, bundle)
    if not paths["income"].exists():
        return [], []

    income = _read_simfin_csv(paths["income"])
    balance = _read_simfin_csv(paths["balance"]) if paths["balance"].exists() else pd.DataFrame()
    cashflow = (
        _read_simfin_csv(paths["cashflow"])
        if paths["cashflow"] is not None and paths["cashflow"].exists()
        else pd.DataFrame()
    )

    ticker_col = mapping["meta"]["ticker"]
    report_col = mapping["meta"]["report_date"]
    curated_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []

    if tickers is not None:
        income = income.loc[income[ticker_col].isin(tickers)]

    balance_by_ticker = _index_statement_by_ticker(
        balance,
        ticker_col=ticker_col,
        report_col=report_col,
    )
    cashflow_by_ticker = _index_statement_by_ticker(
        cashflow,
        ticker_col=ticker_col,
        report_col=report_col,
    )

    work_tickers = _work_tickers(income, ticker_col=ticker_col, tickers=tickers)
    ticker_iter = _ticker_progress_iter(work_tickers, enabled=show_progress)
    exact_balance_match = bundle.income_variant != "ttm"

    for ticker in ticker_iter:
        ticker_income = income.loc[income[ticker_col] == ticker]
        for _, income_row in ticker_income.iterrows():
            if ticker not in company_lookup.index:
                issue_rows.append(_issue_row(ticker=ticker, reason="missing_company_metadata"))
                continue

            company = company_lookup.loc[ticker]
            cik_raw = company.get(mapping["meta"]["cik"])
            if pd.isna(cik_raw) or not str(cik_raw).strip():
                issue_rows.append(_issue_row(ticker=ticker, reason="missing_cik"))
                continue

            cik = pad_cik(str(cik_raw))
            if not is_valid_cik(cik):
                issue_rows.append(_issue_row(ticker=ticker, reason="invalid_cik"))
                continue

            report_date = income_row[report_col]
            balance_row = _matching_statement_row(
                balance_by_ticker,
                ticker=ticker,
                report_date=report_date,
                report_col=report_col,
                exact_match=exact_balance_match,
            )
            if balance_row is None:
                issue_rows.append(_issue_row(ticker=ticker, reason="missing_balance_row"))
                continue

            cashflow_row = None
            if paths["cashflow"] is not None:
                cashflow_row = _matching_statement_row(
                    cashflow_by_ticker,
                    ticker=ticker,
                    report_date=report_date,
                    report_col=report_col,
                    exact_match=True,
                )

            row, issues = _build_curated_row(
                income_row=income_row,
                balance_row=balance_row,
                cashflow_row=cashflow_row,
                ticker=ticker,
                cik=cik,
                mapping=mapping,
                statement_variant=bundle.income_variant,
                enforce_qv_fields=bundle.enforce_qv_fields,
            )
            if issues:
                issue_rows.extend(issues)
            if row is not None:
                curated_rows.append(row)

    return curated_rows, issue_rows


def _write_curated_fundamentals(
    data_dir: Path,
    curated_rows: list[dict[str, object]],
    *,
    show_progress: bool = False,
) -> int:
    """Write curated rows to per-partition parquet (bulk path, same lake layout)."""
    if not curated_rows:
        return 0

    frame = pd.DataFrame(curated_rows)
    grouped = frame.groupby(["cik", "period"], sort=False)

    for parent in {
        curated_fundamentals_path(data_dir, cik=str(cik), period=str(period)).parent
        for cik, period in grouped.groups
    }:
        parent.mkdir(parents=True, exist_ok=True)

    partitions: list[tuple[Path, pd.DataFrame]] = []
    for (cik, period), group in grouped:
        out_path = curated_fundamentals_path(
            data_dir,
            cik=str(cik),
            period=str(period),
        )
        deduped = (
            group.drop_duplicates(subset=["statement_variant"], keep="last")
            if "statement_variant" in group.columns
            else group.iloc[[-1]]
        )
        partitions.append((out_path, deduped))

    if len(partitions) == 1:
        partitions[0][1].to_parquet(partitions[0][0], index=False)
    elif show_progress:
        with (
            click.progressbar(
                length=len(partitions),
                label="Writing curated partitions",
                show_eta=True,
            ) as bar,
            ThreadPoolExecutor(max_workers=_WRITE_WORKERS) as pool,
        ):
            futures = [pool.submit(_write_partition, item) for item in partitions]
            for future in as_completed(futures):
                future.result()
                bar.update(1)
    else:
        with ThreadPoolExecutor(max_workers=_WRITE_WORKERS) as pool:
            list(pool.map(_write_partition, partitions, chunksize=128))

    return len(curated_rows)


def _resolve_show_progress(show_progress: bool | None) -> bool:
    if show_progress is None:
        return sys.stderr.isatty()
    return show_progress


def _work_tickers(
    income: pd.DataFrame,
    *,
    ticker_col: str,
    tickers: set[str] | None,
) -> list[str]:
    """Return sorted tickers to process (scoped set intersected with income rows)."""
    income_tickers = {str(ticker) for ticker in income[ticker_col].unique()}
    if tickers is not None:
        work = sorted(ticker for ticker in tickers if ticker in income_tickers)
        skipped = len(tickers) - len(work)
        if skipped:
            logger.info("%d scoped ticker(s) have no income rows", skipped)
        return work
    return sorted(income_tickers)


def _ticker_progress_iter(work_tickers: list[str], *, enabled: bool):
    if not enabled or not work_tickers:
        yield from work_tickers
        return
    with click.progressbar(
        length=len(work_tickers),
        label="Normalizing tickers",
        show_eta=True,
    ) as bar:
        for ticker in work_tickers:
            yield ticker
            bar.update(1)


def _write_partition(item: tuple[Path, pd.DataFrame]) -> None:
    path, frame = item
    frame.to_parquet(path, index=False)


def _raw_paths_for_bundle(
    data_dir: Path,
    snapshot_date: date,
    bundle: StatementBundle,
) -> dict[str, Path | None]:
    cashflow_path = None
    if bundle.cashflow_variant is not None:
        cashflow_path = simfin_bulk_path(
            data_dir,
            dataset="cashflow",
            variant=bundle.cashflow_variant,
            market="us",
            as_of_date=snapshot_date,
        )
    return {
        "income": simfin_bulk_path(
            data_dir,
            dataset="income",
            variant=bundle.income_variant,
            market="us",
            as_of_date=snapshot_date,
        ),
        "balance": simfin_bulk_path(
            data_dir,
            dataset="balance",
            variant=bundle.balance_variant,
            market="us",
            as_of_date=snapshot_date,
        ),
        "cashflow": cashflow_path,
    }


def _raw_paths(data_dir: Path, snapshot_date: date) -> dict[str, Path]:
    """Demo TTM paths (tests and legacy callers)."""
    bundle_paths = _raw_paths_for_bundle(
        data_dir,
        snapshot_date,
        STATEMENT_BUNDLES[0],
    )
    companies = simfin_bulk_path(
        data_dir,
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=snapshot_date,
    )
    return {
        "income": bundle_paths["income"],
        "balance": bundle_paths["balance"],
        "companies": companies,
    }


def _read_simfin_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", parse_dates=list(DATE_COLUMNS))


def _index_statement_by_ticker(
    frame: pd.DataFrame,
    *,
    ticker_col: str,
    report_col: str,
) -> dict[str, pd.DataFrame]:
    """Pre-group statement rows by ticker sorted by report date."""
    if frame.empty:
        return {}
    indexed: dict[str, pd.DataFrame] = {}
    for ticker, group in frame.groupby(ticker_col, sort=False):
        indexed[str(ticker)] = group.sort_values(report_col)
    return indexed


def _index_balance_by_ticker(
    balance: pd.DataFrame,
    *,
    ticker_col: str,
    report_col: str,
) -> dict[str, pd.DataFrame]:
    """Alias kept for tests importing the demo helper name."""
    return _index_statement_by_ticker(
        balance,
        ticker_col=ticker_col,
        report_col=report_col,
    )


def _matching_statement_row(
    rows_by_ticker: dict[str, pd.DataFrame],
    *,
    ticker: str,
    report_date: pd.Timestamp,
    report_col: str,
    exact_match: bool,
) -> pd.Series | None:
    group = rows_by_ticker.get(ticker)
    if group is None:
        return None
    if exact_match:
        subset = group.loc[group[report_col] == report_date]
        if subset.empty:
            return None
        return subset.iloc[-1]
    subset = group.loc[group[report_col] <= report_date]
    if subset.empty:
        return None
    return subset.iloc[-1]


def _latest_balance_row(
    balance_by_ticker: dict[str, pd.DataFrame],
    *,
    ticker: str,
    report_date: pd.Timestamp,
    report_col: str,
) -> pd.Series | None:
    """Demo TTM join: latest balance on or before income report date."""
    return _matching_statement_row(
        balance_by_ticker,
        ticker=ticker,
        report_date=report_date,
        report_col=report_col,
        exact_match=False,
    )


def _build_curated_row(
    *,
    income_row: pd.Series,
    balance_row: pd.Series,
    cashflow_row: pd.Series | None,
    ticker: str,
    cik: str,
    mapping: dict,
    statement_variant: str,
    enforce_qv_fields: bool,
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    meta = mapping["meta"]
    fields = mapping["fields"]
    issues: list[dict[str, object]] = []

    publish_col = meta["publish_date"]
    report_col = meta["report_date"]
    publish_date = income_row.get(publish_col)
    report_date = income_row[report_col]
    restated_date = income_row.get(meta["restated_date"])
    as_of_date, as_of_source = _resolve_as_of_date(
        publish_date=publish_date,
        report_date=report_date,
        restated_date=restated_date,
        lag_days=int(mapping["missing_publish_lag_days"]),
    )
    if as_of_source == "report_date_lag":
        issues.append(_issue_row(ticker=ticker, reason="missing_publish_date"))
        return None, issues

    currency = income_row.get(meta["currency"])
    if pd.notna(currency) and str(currency).upper() != "USD":
        issues.append(_issue_row(ticker=ticker, reason="non_usd_currency"))
        return None, issues

    fiscal_period_end = report_date.date() if hasattr(report_date, "date") else report_date
    period = _period_label(income_row, meta, fiscal_period_end)
    if not is_valid_fiscal_period(period):
        issues.append(_issue_row(ticker=ticker, reason="invalid_period"))
        return None, issues
    version_id = _version_id(income_row, meta)

    row: dict[str, object] = {
        "cik": cik,
        "ticker": ticker,
        "fiscal_period_end": fiscal_period_end,
        "as_of_date": as_of_date,
        "version_id": version_id,
        "period": period,
        "statement_variant": statement_variant,
        "mapping_version": mapping["version"],
        "currency": "USD",
        "as_of_source": as_of_source,
    }

    statement_sources = (income_row, balance_row, cashflow_row)
    for canonical, simfin_col in fields.items():
        row[canonical] = _field_value(simfin_col, statement_sources)

    if _missing_mandatory(row):
        issues.append(_issue_row(ticker=ticker, reason="missing_mandatory_fields"))
        return None, issues

    if enforce_qv_fields and _missing_qv_fields(row, mapping):
        issues.append(_issue_row(ticker=ticker, reason="missing_qv_inputs"))
        return None, issues

    if as_of_date < fiscal_period_end:
        issues.append(_issue_row(ticker=ticker, reason="as_of_before_period_end"))
        return None, issues

    return row, issues


def _field_value(simfin_col: str, sources: tuple[pd.Series | None, ...]) -> float | None:
    for source in sources:
        if source is not None and simfin_col in source.index:
            return _numeric(source.get(simfin_col))
    return None


def _resolve_as_of_date(
    *,
    publish_date: object,
    report_date: pd.Timestamp,
    restated_date: object,
    lag_days: int,
) -> tuple[date, str]:
    if pd.notna(restated_date):
        return pd.Timestamp(restated_date).date(), "restated_date"
    if pd.notna(publish_date):
        return pd.Timestamp(publish_date).date(), "publish_date"
    fallback = pd.Timestamp(report_date) + pd.Timedelta(days=lag_days)
    return fallback.date(), "report_date_lag"


def _period_label(income_row: pd.Series, meta: dict, report_date: date) -> str:
    fiscal_year = income_row.get(meta["fiscal_year"])
    fiscal_period = income_row.get(meta["fiscal_period"])
    if pd.notna(fiscal_year) and pd.notna(fiscal_period):
        return f"{int(fiscal_year)}{fiscal_period}"
    return fiscal_period_label(report_date)


def _version_id(income_row: pd.Series, meta: dict) -> int:
    restated = income_row.get(meta["restated_date"])
    if pd.notna(restated):
        return 2
    return 1


def _numeric(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _missing_mandatory(row: dict[str, object]) -> bool:
    mandatory = (
        "revenue",
        "ebit",
        "net_income",
        "total_assets",
        "total_liabilities",
        "shares_outstanding",
    )
    return any(row.get(field) is None for field in mandatory)


def _missing_qv_fields(row: dict[str, object], mapping: dict) -> bool:
    required = mapping.get("qv_required_fields", [])
    return any(row.get(field) is None for field in required)


def _issue_row(*, ticker: str, reason: str) -> dict[str, str]:
    return {"ticker": ticker, "reason": reason}


def _load_mapping_yaml(path: Path) -> dict:
    """Parse the project mapping YAML (two-level dict + top-level scalars only)."""
    root: dict[str, object] = {}
    section: dict[str, str] | list[str] | None = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if not line.startswith(" ") and ":" in stripped:
            if stripped.endswith(":"):
                name = stripped[:-1]
                if name in {"fields", "meta"}:
                    section = {}
                    root[name] = section
                elif name == "qv_required_fields":
                    section = []
                    root[name] = section
                else:
                    section = None
                continue
            key, _, value = stripped.partition(":")
            parsed: object = int(value.strip()) if value.strip().isdigit() else value.strip()
            root[key.strip()] = parsed
            section = None
            continue
        if isinstance(section, list) and stripped.startswith("- "):
            section.append(stripped[2:].strip())
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if isinstance(section, dict):
            section[key] = value
    return root
