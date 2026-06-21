"""SimFin bulk CSV → curated point-in-time fundamentals parquet."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

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
)

DATE_COLUMNS = ("Report Date", "Publish Date", "Restated Date")
FUNDAMENTALS_NATURAL_KEY = ("cik", "fiscal_period_end", "as_of_date", "version_id")


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
) -> NormalizeResult:
    """Transform raw SimFin bulk CSVs into curated fundamentals parquet."""
    mapping = load_simfin_mapping(mapping_path)
    paths = _raw_paths(data_dir, snapshot_date)

    income = _read_simfin_csv(paths["income"])
    balance = _read_simfin_csv(paths["balance"])
    companies = pd.read_csv(paths["companies"], sep=";", dtype={"CIK": "string"})

    company_lookup = companies.set_index(mapping["meta"]["ticker"], drop=False)
    curated_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []
    effective_run_date = run_date or snapshot_date

    for _, income_row in income.iterrows():
        ticker = str(income_row[mapping["meta"]["ticker"]])
        if tickers is not None and ticker not in tickers:
            continue

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

        report_date = income_row[mapping["meta"]["report_date"]]
        balance_row = _latest_balance_row(
            balance,
            ticker=ticker,
            report_date=report_date,
            ticker_col=mapping["meta"]["ticker"],
            report_col=mapping["meta"]["report_date"],
        )
        if balance_row is None:
            issue_rows.append(_issue_row(ticker=ticker, reason="missing_balance_row"))
            continue

        row, issues = _build_curated_row(
            income_row=income_row,
            balance_row=balance_row,
            ticker=ticker,
            cik=cik,
            mapping=mapping,
        )
        if issues:
            issue_rows.extend(issues)
        if row is not None:
            curated_rows.append(row)

    result = NormalizeResult()
    result.written_rows = _write_curated_rows(data_dir, curated_rows)

    if issue_rows:
        issues_path = curated_issues_path(data_dir, run_date=effective_run_date)
        issues_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(issue_rows).to_parquet(issues_path, index=False)
        result.issue_rows = len(issue_rows)

    return result


def _raw_paths(data_dir: Path, snapshot_date: date) -> dict[str, Path]:
    return {
        "income": simfin_bulk_path(
            data_dir,
            dataset="income",
            variant="ttm",
            market="us",
            as_of_date=snapshot_date,
        ),
        "balance": simfin_bulk_path(
            data_dir,
            dataset="balance",
            variant="quarterly",
            market="us",
            as_of_date=snapshot_date,
        ),
        "companies": simfin_bulk_path(
            data_dir,
            dataset="companies",
            variant=None,
            market="us",
            as_of_date=snapshot_date,
        ),
    }


def _read_simfin_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", parse_dates=list(DATE_COLUMNS))


def _write_curated_rows(data_dir: Path, rows: list[dict[str, object]]) -> int:
    rows_by_path: dict[Path, list[dict[str, object]]] = {}
    for row in rows:
        period = str(row["period"])
        cik = str(row["cik"])
        out_path = curated_fundamentals_path(data_dir, cik=cik, period=period)
        rows_by_path.setdefault(out_path, []).append(row)

    for out_path, partition_rows in rows_by_path.items():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        partition = pd.DataFrame(partition_rows)
        if out_path.exists():
            partition = pd.concat([pd.read_parquet(out_path), partition], ignore_index=True)
        partition = _deduplicate_fundamentals(partition)
        partition.to_parquet(out_path, index=False)

    return len(rows)


def _deduplicate_fundamentals(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.copy()
    for column in ("fiscal_period_end", "as_of_date"):
        rows[column] = pd.to_datetime(rows[column]).dt.date
    return (
        rows.drop_duplicates(subset=list(FUNDAMENTALS_NATURAL_KEY), keep="last")
        .sort_values(list(FUNDAMENTALS_NATURAL_KEY))
        .reset_index(drop=True)
    )


def _latest_balance_row(
    balance: pd.DataFrame,
    *,
    ticker: str,
    report_date: pd.Timestamp,
    ticker_col: str,
    report_col: str,
) -> pd.Series | None:
    subset = balance.loc[(balance[ticker_col] == ticker) & (balance[report_col] <= report_date)]
    if subset.empty:
        return None
    return subset.sort_values(report_col).iloc[-1]


def _build_curated_row(
    *,
    income_row: pd.Series,
    balance_row: pd.Series,
    ticker: str,
    cik: str,
    mapping: dict,
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
        "mapping_version": mapping["version"],
        "currency": "USD",
        "as_of_source": as_of_source,
    }

    for canonical, simfin_col in fields.items():
        source = income_row if simfin_col in income_row.index else balance_row
        row[canonical] = _numeric(source.get(simfin_col))

    if _missing_mandatory(row):
        issues.append(_issue_row(ticker=ticker, reason="missing_mandatory_fields"))
        return None, issues

    if as_of_date < fiscal_period_end:
        issues.append(_issue_row(ticker=ticker, reason="as_of_before_period_end"))
        return None, issues

    return row, issues


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


def _issue_row(*, ticker: str, reason: str) -> dict[str, str]:
    return {"ticker": ticker, "reason": reason}


def _load_mapping_yaml(path: Path) -> dict:
    """Parse the project mapping YAML (two-level dict + top-level scalars only)."""
    root: dict[str, object] = {}
    section: dict[str, str] | None = None
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
                else:
                    section = None
                continue
            key, _, value = stripped.partition(":")
            parsed: object = int(value.strip()) if value.strip().isdigit() else value.strip()
            root[key.strip()] = parsed
            section = None
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if section is not None:
            section[key] = value
    return root
