# Contract: `credit-css doctor`

**Feature**: `specs/016-credit-css-doctor`  
**Date**: 2026-10-19

## Invocation

```bash
uv run credit-css doctor
# or: python -m credit doctor
```

- **Args**: none in v1
- **Network**: none
- **Exit code**: `0` after printing the report (report-only), including when paths/env are absent

## stdout (human-readable)

One field per line (label then value). Boolean values MUST be `yes` or `no` (lowercase).

| Line label | Value |
| --- | --- |
| `package_version:` | credit package version string |
| `python_version:` | Python runtime version string |
| `cwd:` | current working directory |
| `path_credit_data:` | `yes` \| `no` |
| `path_competition_raw:` | `yes` \| `no` |
| `env_CREDIT_PIPELINE_ARTIFACT_set:` | `yes` \| `no` |
| `env_CREDIT_PIPELINE_ARTIFACT_file_exists:` | `yes` \| `no` |

Example (illustrative):

```text
package_version: 0.1.0
python_version: 3.11.9
cwd: /path/to/SmartWealthAI
path_credit_data: yes
path_competition_raw: no
env_CREDIT_PIPELINE_ARTIFACT_set: no
env_CREDIT_PIPELINE_ARTIFACT_file_exists: no
```

## Forbidden in stdout / stderr

- Value of `CREDIT_PIPELINE_ARTIFACT` (or any planted secret string used in tests)
- Resolved artifact filesystem path string when env is set
- Any `SIMFIN_*` or investing credential material
- JSON blob (out of scope)

## Help surface

- `credit-css doctor --help` exits 0 and mentions readiness / diagnostics.
- Top-level `credit-css --help` / default listing SHOULD mention `doctor` among stages (same pattern as `psi`).

## Test contract (hermetic)

1. `CliRunner().invoke(main, ["doctor"])` → exit code 0; all labels present.
2. With env `CREDIT_PIPELINE_ARTIFACT=/tmp/doctor-secret-path-XYZ/pipeline.joblib` (file need not exist): output contains `env_CREDIT_PIPELINE_ARTIFACT_set: yes`, `env_CREDIT_PIPELINE_ARTIFACT_file_exists: no`, and does **not** contain `doctor-secret-path-XYZ` or the full path string.
