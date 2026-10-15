# Credit CSS batch score — loads pipeline.joblib and scores a mounted mart.
# Build from repo root: docker build -f credit/Dockerfile -t credit-css-score .
# FastAPI serving of the same artifact: credit/Dockerfile.serve

FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app

# System deps for xgboost / scipy wheels when needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

COPY pyproject.toml uv.lock README.md ./
COPY credit ./credit
# Workspace lockfile needs sibling member metadata present.
COPY investing/pyproject.toml investing/pyproject.toml

RUN uv sync --frozen --no-dev --package credit --no-editable

ENV PATH="/app/.venv/bin:$PATH"

# Default: batch score. Mount mart + artifact + output dir at runtime.
# See credit/README.md for a one-liner docker run.
ENTRYPOINT ["credit-css", "score"]
