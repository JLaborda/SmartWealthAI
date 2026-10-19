# Data Model: credit-css doctor

**Feature**: `specs/016-credit-css-doctor`  
**Date**: 2026-10-19

This feature does not persist data. The “model” is the in-memory readiness snapshot printed once to stdout.

## Entity: Readiness Snapshot

| Field | Type | Rules |
| --- | --- | --- |
| package_version | string | Non-empty; equals installed `credit` package version |
| python_version | string | Runtime version string (e.g. `3.11.x`); identity only |
| cwd | string | Absolute or as-reported current working directory path (cwd is not a secret) |
| path_credit_data | boolean | `Path.cwd() / "credit/data"` exists and is a directory |
| path_competition_raw | boolean | `Path.cwd() / "data/credit/raw"` exists and is a directory |
| env_artifact_set | boolean | `CREDIT_PIPELINE_ARTIFACT` is set to a non-empty string |
| env_artifact_file_exists | boolean | If set: `Path(value).expanduser()` exists and is a file; if unset: `false` |

### Validation / invariants

- Snapshot MUST NOT include the value of `CREDIT_PIPELINE_ARTIFACT` or any other secret.
- Snapshot MUST NOT include the resolved artifact path string.
- Snapshot MUST NOT include SIMFIN or investing env keys.
- No application data files are opened or parsed.

## Entity: Closed Checklist

Fixed set (v1) — not user-extensible:

1. Directory: `credit/data/`
2. Directory: `data/credit/raw/`
3. Env: `CREDIT_PIPELINE_ARTIFACT` → two booleans (set, file exists)

## Relationships

- Closed Checklist defines which boolean fields appear on Readiness Snapshot.
- No state transitions; each `doctor` invocation produces a fresh snapshot.
