# Quickstart: credit-css doctor

**Feature**: `specs/016-credit-css-doctor`  
**Contract**: [contracts/doctor-cli.md](./contracts/doctor-cli.md)

## Prerequisites

- Repo checkout; uv env with credit package (`make install-credit` or `uv sync --frozen --package credit --group dev`)
- Run from **repository root** (path booleans are cwd-relative)

## Manual validation

```bash
cd /path/to/SmartWealthAI
uv run credit-css doctor
```

**Expect**: exit 0; lines for `package_version`, `python_version`, `cwd`, both `path_*`, both `env_CREDIT_PIPELINE_ARTIFACT_*` labels; booleans `yes`/`no` only.

Optional: unset vs set artifact env and confirm booleans flip without printing the path:

```bash
unset CREDIT_PIPELINE_ARTIFACT
uv run credit-css doctor
export CREDIT_PIPELINE_ARTIFACT=/tmp/does-not-exist-doctor-test/pipeline.joblib
uv run credit-css doctor
# output must not contain "/tmp/does-not-exist-doctor-test"
```

## Automated validation

```bash
uv run --package credit pytest credit/tests/test_cli_doctor.py -q
# or after domain sync: make test-credit  # includes the new test once added
```

**Expect**: tests green; secret/path non-leak assertions pass.

## Done when

- Manual `doctor` matches [contracts/doctor-cli.md](./contracts/doctor-cli.md)
- Hermetic test covers FR-007 (secret-safety)
- Living Spec status can move to done without mart/scoring/AWS diffs
