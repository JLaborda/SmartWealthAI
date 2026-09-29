"""Build a validated application mart from local demo source data (#144)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

MART_FILENAME = "application_mart.parquet"
REJECTS_FILENAME = "rejects.parquet"
README_FILENAME = "README.md"


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

    frame = pd.read_csv(source_path)
    retained, rejects = _partition_rows(
        frame,
        application_id_column=application_id_column,
        target_column=target_column,
        bad_value=bad_value,
        good_value=good_value,
    )

    mart_path = output_dir / MART_FILENAME
    retained.to_parquet(mart_path, index=False)

    rejects_path = output_dir / REJECTS_FILENAME
    rejects.to_parquet(rejects_path, index=False)

    split_policy = _resolve_split_policy(frame, decision_date_column)
    readme_path = output_dir / README_FILENAME
    readme_path.write_text(
        _mart_readme(
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


def _partition_rows(
    frame: pd.DataFrame,
    *,
    application_id_column: str,
    target_column: str,
    bad_value: object,
    good_value: object,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split source rows into retained mart rows and explicit rejects."""
    allowed = {bad_value, good_value}
    seen_ids: set[object] = set()
    retained_records: list[dict[str, object]] = []
    reject_records: list[dict[str, object]] = []

    for row in frame.to_dict(orient="records"):
        app_id = row.get(application_id_column)
        target_raw = row.get(target_column)

        if pd.isna(app_id) or (isinstance(app_id, str) and not str(app_id).strip()):
            reject_records.append({**row, "reject_reason": "missing_application_id"})
            continue

        if app_id in seen_ids:
            reject_records.append({**row, "reject_reason": "duplicate_application_id"})
            continue

        if pd.isna(target_raw):
            reject_records.append({**row, "reject_reason": "missing_target"})
            continue

        target_num = pd.to_numeric(target_raw, errors="coerce")
        if pd.isna(target_num) or target_num not in allowed:
            reject_records.append({**row, "reject_reason": "invalid_target"})
            continue

        seen_ids.add(app_id)
        clean = dict(row)
        clean[application_id_column] = int(app_id) if float(app_id) == int(app_id) else app_id
        clean[target_column] = int(target_num)
        retained_records.append(clean)

    retained = pd.DataFrame(retained_records, columns=list(frame.columns))
    reject_columns = list(frame.columns) + ["reject_reason"]
    rejects = pd.DataFrame(reject_records, columns=reject_columns)
    return retained, rejects


def _resolve_split_policy(
    frame: pd.DataFrame,
    decision_date_column: str | None,
) -> str:
    if decision_date_column and decision_date_column in frame.columns:
        return "time_based"
    return "stratified_random"


def _mart_readme(
    *,
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

## Target → bad / good

| Column | Bad (positive class) | Good (negative class) |
| --- | --- | --- |
| `{target_column}` | `{bad_value}` | `{good_value}` |

Domain language: **bad** = default / payment difficulties under the dataset dictionary; \
**good** = no default event under that definition.

## Build counts

- Retained rows: {retained_rows}
- Rejected rows: {rejected_rows}

Rejected rows are also written to `{REJECTS_FILENAME}` with a `reject_reason` column.

## Develop / holdout

{split_doc}
"""
