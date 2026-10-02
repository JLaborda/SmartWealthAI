# Credit CSS batch score — loads pipeline.joblib and scores a mounted mart.
# Build from repo root: docker build -f credit/Dockerfile -t credit-css-score .
# FastAPI serving of the same artifact is a later PR (not this image).

FROM python:3.11-slim-bookworm

WORKDIR /app

# System deps for xgboost / scipy wheels when needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock README.md ./
COPY src ./src
COPY credit ./credit

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-ansi --no-interaction

# Default: batch score. Mount mart + artifact + output dir at runtime.
# See credit/README.md for a one-liner docker run.
ENTRYPOINT ["credit-css", "score"]
