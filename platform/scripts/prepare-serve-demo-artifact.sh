#!/usr/bin/env bash
# Hermetic fit → credit/demo_artifact/pipeline.joblib for Dockerfile.serve.demo (#173).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

OUT="${CREDIT_DEMO_ARTIFACT_DIR:-$ROOT/credit/demo_artifact}"

poetry run python -c "
from pathlib import Path
from credit.demo_serve_artifact import prepare_serve_demo_artifact
path = prepare_serve_demo_artifact(Path(r'''$OUT'''))
print(path)
"
