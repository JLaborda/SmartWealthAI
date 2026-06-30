"""edgartools client for standardized annual financial statements.

Uses ``Company(ticker).get_facts()`` and extracts annual income, balance, and cash-flow
statements via ``.income_statement()``, ``.balance_sheet()``, and
``.cashflow_statement()`` — matching the notebook exploration pattern.

Output parquets preserve the edgartools dataframe shape (``concept``, ``label``, ``section``,
``FY 20xx`` columns).

Operator guide: ``docs/mvp/guides/download-fundamentals.md``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from edgar import Company, set_identity

from smartwealthai.lake_paths import STATEMENT_NAMES
from smartwealthai.sec_client import get_sec_identity


class EdgartoolsClientError(Exception):
    """Raised when edgartools statement extraction or parquet write fails."""


def configure_identity() -> None:
    """Set edgartools identity from ``SEC_IDENTITY`` (same value as SEC REST User-Agent)."""
    set_identity(get_sec_identity())


def _statement_to_dataframe(facts: object, statement: str, periods: int) -> pd.DataFrame:
    """Convert one edgartools statement object to a pandas DataFrame."""
    if statement == "income_statement":
        statement_obj = facts.income_statement(periods=periods, period="annual")
    elif statement == "balance_sheet":
        statement_obj = facts.balance_sheet(periods=periods, period="annual")
    elif statement == "cashflow_statement":
        statement_obj = facts.cashflow_statement(periods=periods, period="annual")
    else:
        msg = f"Unknown statement: {statement}"
        raise ValueError(msg)
    return statement_obj.to_dataframe()


def download_statements(
    ticker: str,
    paths_by_statement: dict[str, Path],
    *,
    periods: int,
    force: bool = False,
) -> list[str]:
    """Download annual statements and write parquet files.

    Calls ``get_facts()`` once per ticker, then writes up to three statement parquets.
    Skips individual statements when the target file exists and ``force`` is False.

    Args:
        ticker: Trading symbol for ``edgartools.Company``.
        paths_by_statement: Map of statement name → output parquet path.
        periods: Number of annual fiscal periods (e.g. 16 ≈ 16 years of FY columns).
        force: When True, overwrite existing parquet files.

    Returns:
        List of statement names that were skipped (already on disk).

    Raises:
        EdgartoolsClientError: Propagated from underlying library failures (wrapped by caller).
        ValueError: On unknown statement keys in ``paths_by_statement``.
    """
    configure_identity()
    company = Company(ticker)
    facts = company.get_facts()

    skipped: list[str] = []
    for statement in STATEMENT_NAMES:
        output_path = paths_by_statement[statement]
        if output_path.exists() and not force:
            skipped.append(statement)
            continue

        frame = _statement_to_dataframe(facts, statement, periods)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(output_path, index=True)
    return skipped
