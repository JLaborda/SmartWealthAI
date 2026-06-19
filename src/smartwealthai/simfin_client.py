"""Thin wrapper around the ``simfin`` package for bulk dataset downloads."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import simfin as sf
from simfin.paths import _path_dataset

LoadFn = Callable[..., None]


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


def fetch_dataset_csv(
    *,
    dataset: str,
    variant: str | None,
    market: str | None,
    refresh_days: int,
    load_fn: LoadFn | None = None,
) -> Path:
    """Download (if needed) and return the simfin cache CSV path."""
    loader = load_fn or _default_loader(dataset)
    kwargs: dict[str, object] = {"refresh_days": refresh_days}
    if variant is not None:
        kwargs["variant"] = variant
    if market is not None and dataset == "companies":
        kwargs["market"] = market
    loader(**kwargs)
    return dataset_cache_path(dataset=dataset, variant=variant, market=market)


def _default_loader(dataset: str) -> LoadFn:
    loaders = {
        "companies": sf.load_companies,
        "industries": sf.load_industries,
        "income": sf.load_income,
        "balance": sf.load_balance,
        "cashflow": sf.load_cashflow,
    }
    try:
        return loaders[dataset]
    except KeyError as exc:
        msg = f"Unknown SimFin dataset: {dataset}"
        raise ValueError(msg) from exc
