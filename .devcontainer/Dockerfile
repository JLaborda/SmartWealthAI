FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        make \
        jq \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*
