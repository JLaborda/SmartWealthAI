"""Lake root URI resolution and storage-backend I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import pandas as pd

from smartwealthai import lake_paths

Backend = Literal["file", "s3"]


@dataclass(frozen=True)
class LakeRoot:
    """Configurable data lake root with zone-relative path builders."""

    backend: Backend
    uri: str
    _path: Path | None = None
    s3_bucket: str | None = None
    s3_prefix: str | None = None

    def as_path(self) -> Path:
        """Return the local filesystem root (file backend only)."""
        if self.backend != "file":
            msg = f"S3 lake root has no local Path; use lake I/O helpers: {self.uri}"
            raise TypeError(msg)
        if self._path is None:
            msg = f"File lake root is missing a path: {self.uri}"
            raise ValueError(msg)
        return self._path

    def curated_portfolio_path(self, *, run_date: date) -> Path:
        """Build the curated portfolio parquet path for a run date."""
        if self.backend != "file":
            msg = "curated_portfolio_path is implemented for the file backend in this slice"
            raise NotImplementedError(msg)
        return lake_paths.curated_portfolio_path(self.as_path(), run_date=run_date)

    def write_parquet(self, path: Path, frame: pd.DataFrame) -> None:
        """Write a parquet artifact under the lake root."""
        if self.backend != "file":
            msg = "S3 parquet writes are not implemented in this slice; use file:// locally"
            raise NotImplementedError(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)

    def read_parquet(self, path: Path) -> pd.DataFrame:
        """Read a parquet artifact from the lake root."""
        if self.backend != "file":
            msg = "S3 parquet reads are not implemented in this slice; use file:// locally"
            raise NotImplementedError(msg)
        return pd.read_parquet(path)


def resolve_lake_root(uri: str | None) -> LakeRoot:
    """Parse a lake root URI into a :class:`LakeRoot`.

    Supported forms:
    - ``file:///absolute/path`` or ``file://relative/path``
    - bare local path (``data``, ``/tmp/lake``)
    - ``s3://bucket/prefix`` (parsed for cloud workflows; file I/O stays local here)
    """
    if uri is None or not str(uri).strip():
        msg = "Lake root URI is required"
        raise ValueError(msg)

    raw = str(uri).strip()
    if raw.startswith("s3://"):
        return _resolve_s3(raw)
    if raw.startswith("file://"):
        return _resolve_file(raw)
    if "://" in raw:
        scheme = urlparse(raw).scheme
        msg = f"Unsupported lake root URI scheme: {scheme!r}"
        raise ValueError(msg)
    return _resolve_file(raw)


def _resolve_file(uri: str) -> LakeRoot:
    if uri.startswith("file://"):
        parsed = urlparse(uri)
        if parsed.netloc:
            path = Path(f"/{parsed.netloc}{parsed.path}")
        else:
            path = Path(parsed.path)
    else:
        path = Path(uri)
    resolved = path.expanduser().resolve()
    return LakeRoot(backend="file", uri=uri, _path=resolved)


def _resolve_s3(uri: str) -> LakeRoot:
    parsed = urlparse(uri)
    bucket = parsed.netloc
    if not bucket:
        msg = f"Invalid S3 lake root URI: {uri!r}"
        raise ValueError(msg)
    prefix = parsed.path.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return LakeRoot(backend="s3", uri=uri, s3_bucket=bucket, s3_prefix=prefix or "")
