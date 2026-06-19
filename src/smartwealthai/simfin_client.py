"""Thin wrapper around the ``simfin`` package for bulk dataset downloads."""

from __future__ import annotations

import os
import zipfile
from collections.abc import Callable
from pathlib import Path

import simfin as sf
from simfin.download import _download, _headers_dataset, _url_dataset
from simfin.paths import _path_dataset, _path_download_dataset
from simfin.utils import _file_age

DownloadFn = Callable[..., None]

KNOWN_DATASETS = frozenset({"companies", "industries", "income", "balance", "cashflow"})


def configure_simfin(*, api_key: str, cache_dir: Path) -> None:
    """Point the simfin package at a local cache directory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    sf.set_api_key(api_key)
    sf.set_data_dir(str(cache_dir))


def dataset_cache_path(
    *,
    dataset: str,
    variant: str | None,
    market: str | None,
) -> Path:
    """Return the CSV path used by the simfin package on disk."""
    return Path(_path_dataset(dataset=dataset, variant=variant, market=market))


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """Extract ZIP members only under ``dest_dir`` (zip-slip guard)."""
    root = dest_dir.resolve()
    root_prefix = os.path.join(str(root), "")
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (root / member.filename).resolve()
            if not str(target).startswith(root_prefix):
                msg = f"Unsafe zip entry path: {member.filename!r}"
                raise ValueError(msg)
            archive.extract(member, root)


def _normalize_dataset_args(
    dataset: str,
    variant: str | None,
    market: str | None,
) -> tuple[str, str | None, str | None]:
    normalized = dataset.lower()
    normalized_variant = variant.lower() if variant is not None else None
    normalized_market = market.lower() if market is not None else None
    return normalized, normalized_variant, normalized_market


def _must_download(csv_path: Path, *, refresh_days: int) -> bool:
    if refresh_days == 0 or not csv_path.exists():
        return True
    return _file_age(str(csv_path)).days >= refresh_days


def download_dataset_csv(
    *,
    dataset: str,
    variant: str | None,
    market: str | None,
    refresh_days: int,
) -> None:
    """Download a SimFin bulk CSV when missing or stale (safe ZIP extraction)."""
    if dataset not in KNOWN_DATASETS:
        msg = f"Unknown SimFin dataset: {dataset}"
        raise ValueError(msg)

    dataset, variant, market = _normalize_dataset_args(dataset, variant, market)
    kwargs: dict[str, str | None] = {"dataset": dataset, "variant": variant, "market": market}
    csv_path = dataset_cache_path(dataset=dataset, variant=variant, market=market)
    if not _must_download(csv_path, refresh_days=refresh_days):
        return

    download_path = Path(_path_download_dataset(**kwargs))
    _download(
        url=_url_dataset(**kwargs),
        headers=_headers_dataset(),
        download_path=str(download_path),
    )

    data_dir = Path(sf.config.get_data_dir())
    if download_path.suffix == ".zip":
        safe_extract_zip(download_path, data_dir)
    else:
        download_path.replace(csv_path)


def fetch_dataset_csv(
    *,
    dataset: str,
    variant: str | None,
    market: str | None,
    refresh_days: int,
    download_fn: DownloadFn | None = None,
) -> Path:
    """Download (if needed) and return the simfin cache CSV path."""
    downloader = download_fn or download_dataset_csv
    downloader(
        dataset=dataset,
        variant=variant,
        market=market,
        refresh_days=refresh_days,
    )
    return dataset_cache_path(dataset=dataset, variant=variant, market=market)
