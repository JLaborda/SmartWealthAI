"""Shared lake root resolution for pipeline CLIs."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from smartwealthai.lake_root import LakeRoot, resolve_lake_root


def lake_root_options(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Attach ``--lake-root-uri`` and ``--data-dir`` options to a Click command."""
    fn = click.option(
        "--lake-root-uri",
        envvar="LAKE_ROOT_URI",
        default=None,
        help="Lake root URI (file:// or s3://). Overrides --data-dir.",
    )(fn)
    fn = click.option(
        "--data-dir",
        type=click.Path(path_type=Path, file_okay=False),
        default=None,
        help="Local data lake root (backward compatible; default data/).",
    )(fn)
    return fn


def resolve_cli_lake_root(
    *,
    lake_root_uri: str | None,
    data_dir: Path | None,
) -> LakeRoot:
    """Resolve lake root with CLI/env precedence.

    Order: ``--lake-root-uri`` (includes ``LAKE_ROOT_URI`` via Click) →
    ``--data-dir`` → ``SMARTWEALTHAI_DATA_DIR`` → ``data``.
    """
    if lake_root_uri:
        return resolve_lake_root(lake_root_uri)
    if data_dir is not None:
        return resolve_lake_root(str(data_dir))
    if uri := os.environ.get("SMARTWEALTHAI_DATA_DIR"):
        return resolve_lake_root(uri)
    return resolve_lake_root("data")


def resolve_cli_data_dir(
    *,
    lake_root_uri: str | None,
    data_dir: Path | None,
) -> Path:
    """Return a local :class:`Path` for file-backend pipeline stages."""
    return resolve_cli_lake_root(lake_root_uri=lake_root_uri, data_dir=data_dir).as_path()
