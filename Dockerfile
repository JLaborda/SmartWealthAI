# Pipeline batch image for ingest, normalize, and score-universe on AWS or locally.
# Build: make docker-build
# Run:   docker run --rm -e LAKE_ROOT_URI=file:///lake -v "$PWD/data:/lake" smartwealthai-pipeline score-universe --help

FROM python:3.11-slim-bookworm

WORKDIR /app

ENV POETRY_VERSION=2.1.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    LAKE_ROOT_URI=file:///lake

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
COPY src ./src
COPY config ./config

RUN poetry install --only main

ENTRYPOINT ["score-universe"]
CMD ["--help"]
