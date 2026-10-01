"""Build application marts from local competition raw extracts (#152)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from credit.application_mart import ApplicationMartResult, build_application_mart

SourceKind = Literal["amex", "home_credit"]

_AMEX_STATEMENTS = "train_data.parquet"
_AMEX_LABELS = "train_labels.csv"
_HC_APPLICATION = "application_train.csv"

_ID_COL = {
    "amex": "customer_ID",
    "home_credit": "SK_ID_CURR",
}
_TARGET_COL = {
    "amex": "target",
    "home_credit": "TARGET",
}

# Official AMEX categoricals (competition docs) — collapse with mode + last only.
_AMEX_CATEGORICALS = frozenset(
    {
        "B_30",
        "B_38",
        "D_114",
        "D_116",
        "D_117",
        "D_120",
        "D_126",
        "D_63",
        "D_64",
        "D_66",
        "D_68",
    }
)


def build_competition_mart(
    *,
    source_kind: SourceKind,
    raw_dir: Path,
    output_dir: Path,
) -> ApplicationMartResult:
    """Prepare application-grain table from raw extract → validated application mart."""
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    prepared_dir = output_dir / "_prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    prepared_path = prepared_dir / f"{source_kind}_application_table.parquet"

    if source_kind == "amex":
        prepare_amex_application_table(raw_dir, prepared_path)
    elif source_kind == "home_credit":
        prepare_home_credit_application_table(raw_dir, prepared_path)
    else:
        raise ValueError(f"Unsupported source_kind {source_kind!r}; use 'amex' or 'home_credit'")

    result = build_application_mart(
        prepared_path,
        output_dir,
        application_id_column=_ID_COL[source_kind],
        target_column=_TARGET_COL[source_kind],
        bad_value=1,
        good_value=0,
    )
    _append_source_contract(result.readme_path, source_kind=source_kind, raw_dir=raw_dir)
    return result


def _append_source_contract(
    readme_path: Path,
    *,
    source_kind: SourceKind,
    raw_dir: Path,
) -> None:
    """Append competition prepare contract to the mart README sidecar."""
    if source_kind == "amex":
        cats = ", ".join(sorted(_AMEX_CATEGORICALS))
        contract = f"""
## Competition source contract (AMEX)

- Raw dir: `{raw_dir}`
- Grain: statement-level `{_AMEX_STATEMENTS}` aggregated to **one row per `customer_ID`**
- Aggregation (continuous numerics, ordered by `S_2`): **mean**, **std**, **min**, **max**, **last**
- Aggregation (categoricals, ordered by `S_2`): **mode**, **last** only
- Categorical columns: `{cats}` (plus any other non-numeric statement features)
- Output names: `{{col}}_mode`, `{{col}}_last` (e.g. `D_63_mode`, `D_63_last`)
- Labels: inner join `{_AMEX_LABELS}` (`customer_ID`, `target`)
- Target → bad/good: `target` **1 = bad**, **0 = good** (AMEX default dictionary)
"""
    else:
        contract = f"""
## Competition source contract (Home Credit)

- Raw dir: `{raw_dir}`
- Grain: `{_HC_APPLICATION}` is already **one row per `SK_ID_CURR`** (pass-through prepare)
- Bureau / previous / balance joins: not applied in this cut (optional enrich later)
- Target → bad/good: `TARGET` **1 = bad**, **0 = good** (Home Credit default dictionary)
"""
    with readme_path.open("a", encoding="utf-8") as handle:
        handle.write(contract)


def prepare_amex_application_table(raw_dir: Path, output_path: Path) -> Path:
    """Aggregate statement-level AMEX train parquet + labels → one row per customer."""
    raw_dir = Path(raw_dir)
    output_path = Path(output_path)
    statements_path = raw_dir / _AMEX_STATEMENTS
    labels_path = raw_dir / _AMEX_LABELS
    if not statements_path.is_file():
        raise FileNotFoundError(f"Missing AMEX statements: {statements_path}")
    if not labels_path.is_file():
        raise FileNotFoundError(f"Missing AMEX labels: {labels_path}")

    statements = pd.read_parquet(statements_path)
    if "customer_ID" not in statements.columns:
        raise ValueError("AMEX statements must include customer_ID")
    if "S_2" not in statements.columns:
        raise ValueError("AMEX statements must include S_2 (statement date) for last-* aggregation")

    work = statements.copy()
    work["S_2"] = pd.to_datetime(work["S_2"], errors="coerce")
    work = work.sort_values(["customer_ID", "S_2"], kind="mergesort")

    feature_cols = [c for c in work.columns if c not in {"customer_ID", "S_2"}]
    categorical_cols = [
        c
        for c in feature_cols
        if c in _AMEX_CATEGORICALS or not pd.api.types.is_numeric_dtype(work[c])
    ]
    continuous_cols = [c for c in feature_cols if c not in categorical_cols]

    parts: list[pd.DataFrame] = []
    if continuous_cols:
        # Single groupby.agg keeps the wide feature frame contiguous.
        continuous = work.groupby("customer_ID", sort=False)[continuous_cols].agg(
            ["mean", "std", "min", "max", "last"]
        )
        continuous.columns = [f"{col}_{stat}" for col, stat in continuous.columns]
        parts.append(continuous.reset_index())

    if categorical_cols:
        categorical = work.groupby("customer_ID", sort=False)[categorical_cols].agg(
            [_series_mode, "last"]
        )
        categorical.columns = [f"{col}_{stat}" for col, stat in categorical.columns]
        parts.append(categorical.reset_index())

    if parts:
        features = parts[0]
        for part in parts[1:]:
            features = features.merge(part, on="customer_ID", how="outer")
    else:
        features = (
            work[["customer_ID"]].drop_duplicates(subset=["customer_ID"]).reset_index(drop=True)
        )

    labels = pd.read_csv(labels_path)
    if "customer_ID" not in labels.columns or "target" not in labels.columns:
        raise ValueError("AMEX labels must include customer_ID and target")
    labels = labels[["customer_ID", "target"]].drop_duplicates(subset=["customer_ID"], keep="first")

    table = features.merge(labels, on="customer_ID", how="inner")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(output_path, index=False)
    return output_path


def _series_mode(series: pd.Series) -> object:
    """Most frequent value; first mode on ties. Empty → NA."""
    modes = series.mode(dropna=True)
    if modes.empty:
        return pd.NA
    return modes.iloc[0]


# pandas groupby.agg uses __name__ for the MultiIndex level ("mode", not "_series_mode").
_series_mode.__name__ = "mode"


def prepare_home_credit_application_table(raw_dir: Path, output_path: Path) -> Path:
    """Pass through application_train (already application grain); joins later."""
    raw_dir = Path(raw_dir)
    output_path = Path(output_path)
    source = raw_dir / _HC_APPLICATION
    if not source.is_file():
        raise FileNotFoundError(f"Missing Home Credit application table: {source}")

    table = pd.read_csv(source)
    if "SK_ID_CURR" not in table.columns or "TARGET" not in table.columns:
        raise ValueError("Home Credit application_train must include SK_ID_CURR and TARGET")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(output_path, index=False)
    return output_path
