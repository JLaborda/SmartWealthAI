"""Build a validated application mart from local demo source data (#144, #147)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

MART_FILENAME = "application_mart.parquet"
REJECTS_FILENAME = "rejects.parquet"
README_FILENAME = "README.md"

_PICKLE_SUFFIXES = {".pkl", ".pickle"}


@dataclass(frozen=True)
class ApplicationMartResult:
    """Outcome of one application mart build."""

    retained_rows: int
    rejected_rows: int
    mart_path: Path
    readme_path: Path
    target_column: str
    bad_value: object
    good_value: object
    split_policy: str


def build_application_mart(
    source_path: Path,
    output_dir: Path,
    *,
    application_id_column: str = "SK_ID_CURR",
    target_column: str = "TARGET",
    bad_value: object = 1,
    good_value: object = 0,
    decision_date_column: str | None = None,
) -> ApplicationMartResult:
    """Load local demo source → validate → write application mart + README sidecar."""
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = _load_source_frame(source_path)
    frame = _ensure_application_id_column(frame, application_id_column)
    retained, rejects = _partition_rows(
        frame,
        application_id_column=application_id_column,
        target_column=target_column,
        bad_value=bad_value,
        good_value=good_value,
    )

    retained = _coerce_for_parquet(retained)
    rejects = _coerce_for_parquet(rejects)

    mart_path = output_dir / MART_FILENAME
    retained.to_parquet(mart_path, index=False)

    rejects_path = output_dir / REJECTS_FILENAME
    rejects.to_parquet(rejects_path, index=False)

    split_policy = _resolve_split_policy(frame, decision_date_column)
    readme_path = output_dir / README_FILENAME
    readme_path.write_text(
        _mart_readme(
            source_path=source_path,
            application_id_column=application_id_column,
            target_column=target_column,
            bad_value=bad_value,
            good_value=good_value,
            retained_rows=len(retained),
            rejected_rows=len(rejects),
            split_policy=split_policy,
            decision_date_column=decision_date_column,
        ),
        encoding="utf-8",
    )

    return ApplicationMartResult(
        retained_rows=len(retained),
        rejected_rows=len(rejects),
        mart_path=mart_path,
        readme_path=readme_path,
        target_column=target_column,
        bad_value=bad_value,
        good_value=good_value,
        split_policy=split_policy,
    )


def _load_source_frame(source_path: Path) -> pd.DataFrame:
    """Load CSV or pickle application source (CI fixtures stay CSV)."""
    suffix = source_path.suffix.lower()
    if suffix in _PICKLE_SUFFIXES:
        return pd.read_pickle(source_path)
    if suffix == ".csv":
        return pd.read_csv(source_path)
    raise ValueError(
        f"Unsupported source format '{source_path.suffix}'; use .csv, .pkl, or .pickle"
    )


def _ensure_application_id_column(
    frame: pd.DataFrame,
    application_id_column: str,
) -> pd.DataFrame:
    """Promote index to a column when the application id lives on the index (AMEX sample)."""
    if application_id_column in frame.columns:
        return frame
    if frame.index.name == application_id_column:
        return frame.reset_index()
    raise ValueError(
        f"Application id column '{application_id_column}' not found in columns "
        f"or as index name (index.name={frame.index.name!r})"
    )


def _coerce_for_parquet(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize dtypes so wide float16 / category frames write reliably."""
    if frame.empty:
        return frame
    out = frame.copy()
    for col in out.select_dtypes(include=["float16"]).columns:
        out[col] = out[col].astype("float32")
    for col in out.columns:
        dtype = out[col].dtype
        if isinstance(dtype, pd.CategoricalDtype) or str(dtype) == "category":
            out[col] = out[col].astype(str)
    return out


def _partition_rows(
    frame: pd.DataFrame,
    *,
    application_id_column: str,
    target_column: str,
    bad_value: object,
    good_value: object,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split source rows into retained mart rows and explicit rejects."""
    if target_column not in frame.columns:
        raise ValueError(f"Target column '{target_column}' not found in source")

    work = frame.copy()
    ids = work[application_id_column]
    missing_id = ids.map(_is_blank_id)
    dup_id = ids.duplicated(keep="first") & ~missing_id

    target_num = pd.to_numeric(work[target_column], errors="coerce")
    missing_target = target_num.isna() & ~missing_id & ~dup_id
    allowed = {bad_value, good_value}
    invalid_target = (
        ~missing_id
        & ~dup_id
        & ~missing_target
        & ~target_num.map(lambda v: v in allowed if pd.notna(v) else False)
    )

    reason = pd.Series(pd.NA, index=work.index, dtype="object")
    reason = reason.mask(missing_id, "missing_application_id")
    reason = reason.mask(dup_id & reason.isna(), "duplicate_application_id")
    reason = reason.mask(missing_target & reason.isna(), "missing_target")
    reason = reason.mask(invalid_target & reason.isna(), "invalid_target")

    reject_mask = reason.notna()
    rejects = work.loc[reject_mask].copy()
    rejects["reject_reason"] = reason.loc[reject_mask].to_numpy()

    retained = work.loc[~reject_mask].copy()
    if not retained.empty:
        retained[application_id_column] = retained[application_id_column].map(
            _normalize_application_id
        )
        retained[target_column] = pd.to_numeric(retained[target_column], errors="coerce").astype(
            int
        )

    return retained.reset_index(drop=True), rejects.reset_index(drop=True)


def _is_blank_id(app_id: object) -> bool:
    if pd.isna(app_id):
        return True
    if isinstance(app_id, str) and not app_id.strip():
        return True
    return False


def _normalize_application_id(app_id: object) -> object:
    """Keep string ids (AMEX hashes); coerce integral numerics to int."""
    if isinstance(app_id, str):
        return app_id
    try:
        as_float = float(app_id)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return app_id
    if as_float == int(as_float):
        return int(as_float)
    return app_id


def _resolve_split_policy(
    frame: pd.DataFrame,
    decision_date_column: str | None,
) -> str:
    if decision_date_column and decision_date_column in frame.columns:
        return "time_based"
    return "stratified_random"


def _mart_readme(
    *,
    source_path: Path,
    application_id_column: str,
    target_column: str,
    bad_value: object,
    good_value: object,
    retained_rows: int,
    rejected_rows: int,
    split_policy: str,
    decision_date_column: str | None,
) -> str:
    if split_policy == "time_based":
        split_doc = (
            f"Develop/holdout policy: **time-based** on `{decision_date_column}` "
            "(application/decision date). Partition files are not written in PR1; "
            "scoring stages must split before WOE/model fit."
        )
    else:
        split_doc = (
            "Develop/holdout policy: **stratified random** "
            "(no application/decision date column on this source). "
            "Limitation: a random stratified split is not production-grade when a "
            "decision date exists. Partition files are not written in PR1; "
            "scoring stages must split before WOE/model fit."
        )

    return f"""# Application mart

Public demo data only — not live bank BFSI data.

## Source

- Path: `{source_path}`
- Application id column: `{application_id_column}`

## Target → bad / good

| Column | Bad (positive class) | Good (negative class) |
| --- | --- | --- |
| `{target_column}` | `{bad_value}` | `{good_value}` |

Domain language: **bad** = default / payment difficulties under the dataset dictionary; \
**good** = no default event under that definition.

For the book AMEX-shaped sample (`train_df_sample.pkl`), `{target_column}=1` is default \
(no payment within 120 days after the latest statement in the AMEX performance window) \
and `{target_column}=0` is non-default — same convention as the AMEX Default Prediction \
competition dictionary.

## Build counts

- Retained rows: {retained_rows}
- Rejected rows: {rejected_rows}

Rejected rows are also written to `{REJECTS_FILENAME}` with a `reject_reason` column.

## Develop / holdout

{split_doc}
"""
