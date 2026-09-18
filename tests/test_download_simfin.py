"""Hermetic tests for the SimFin bulk connector (issue #55).

Covers raw-zone path layout, refresh/skip semantics, and mocked downloads.
Live SimFin calls are excluded from PR CI.
"""

from __future__ import annotations

import os
import time
import zipfile
from collections.abc import Callable
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from smartwealthai.download_simfin import (
    DEMO_DATASETS,
    DatasetResult,
    cli_run,
    download_dataset,
    run_download,
    should_skip_dataset,
)
from smartwealthai.lake_paths import (
    simfin_bulk_path,
    simfin_errors_path,
    simfin_source_filename,
)
from smartwealthai.simfin_client import (
    configure_simfin,
    dataset_cache_path,
    download_dataset_csv,
    fetch_dataset_csv,
    safe_extract_zip,
)


def test_simfin_bulk_path_matches_spec_layout() -> None:
    path = simfin_bulk_path(
        Path("data"),
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=date(2026, 6, 18),
    )
    assert path == Path(
        "data/raw/simfin/dataset=income/variant=ttm/market=us/"
        "as_of_date=2026-06-18/us-income-ttm.csv"
    )


def test_simfin_bulk_path_uses_default_variant_for_companies() -> None:
    path = simfin_bulk_path(
        Path("data"),
        dataset="companies",
        variant=None,
        market="us",
        as_of_date=date(2026, 6, 18),
    )
    assert path == Path(
        "data/raw/simfin/dataset=companies/variant=default/market=us/"
        "as_of_date=2026-06-18/us-companies.csv"
    )


def test_should_skip_when_lake_file_is_fresh(tmp_path: Path) -> None:
    target = tmp_path / "us-income-ttm.csv"
    target.write_text("csv")
    now = 1_700_000_000.0
    os.utime(target, (now, now))
    assert should_skip_dataset(target, refresh_days=7, force=False, now=now) is True


def test_should_not_skip_when_lake_file_is_stale(tmp_path: Path) -> None:
    target = tmp_path / "us-income-ttm.csv"
    target.write_text("csv")
    now = 1_700_000_000.0
    stale_mtime = now - (8 * 86400)
    os.utime(target, (stale_mtime, stale_mtime))
    assert should_skip_dataset(target, refresh_days=7, force=False, now=now) is False


def test_should_not_skip_when_force_enabled(tmp_path: Path) -> None:
    target = tmp_path / "us-income-ttm.csv"
    target.write_text("csv")
    now = 1_700_000_000.0
    os.utime(target, (now, now))
    assert should_skip_dataset(target, refresh_days=7, force=True, now=now) is False


def test_should_not_skip_when_lake_file_missing(tmp_path: Path) -> None:
    target = tmp_path / "missing.csv"
    assert should_skip_dataset(target, refresh_days=7, force=False, now=1_700_000_000.0) is False


def test_download_dataset_copies_csv_into_lake_layout(tmp_path: Path) -> None:
    spec = DEMO_DATASETS[2]  # income ttm
    cache_csv = tmp_path / "cache" / "us-income-ttm.csv"
    cache_csv.parent.mkdir(parents=True)
    cache_csv.write_text("Ticker;Revenue\nAAPL;100\n")

    def fake_fetch(**_kwargs: object) -> Path:
        return cache_csv

    result = download_dataset(
        spec,
        data_dir=tmp_path / "lake",
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=False,
        fetch_csv=fake_fetch,
    )

    lake_path = simfin_bulk_path(
        tmp_path / "lake",
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=date(2026, 6, 18),
    )
    assert result == DatasetResult(name="income", downloaded=True)
    assert lake_path.read_text() == cache_csv.read_text()


def test_download_dataset_skips_fresh_lake_copy(tmp_path: Path) -> None:
    spec = DEMO_DATASETS[2]
    lake_root = tmp_path / "lake"
    lake_path = simfin_bulk_path(
        lake_root,
        dataset="income",
        variant="ttm",
        market="us",
        as_of_date=date(2026, 6, 18),
    )
    lake_path.parent.mkdir(parents=True, exist_ok=True)
    lake_path.write_text("existing\n")
    now = 1_700_000_000.0
    os.utime(lake_path, (now, now))

    def fail_fetch(**_kwargs: object) -> Path:
        raise AssertionError("fetch should not run for a fresh lake copy")

    result = download_dataset(
        spec,
        data_dir=lake_root,
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=False,
        fetch_csv=fail_fetch,
        now=now,
    )
    assert result == DatasetResult(name="income", skipped=True)


def test_run_download_continues_after_noncritical_failure(tmp_path: Path) -> None:
    data_dir = tmp_path / "lake"
    cache_dir = tmp_path / "cache"

    def fake_fetch(
        *,
        dataset: str,
        variant: str | None,
        market: str | None,
        **_kwargs: object,
    ) -> Path:
        if dataset == "cashflow":
            msg = "simfin unavailable"
            raise OSError(msg)
        path = cache_dir / f"{market or 'global'}-{dataset}-{variant or 'default'}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("csv\n")
        return path

    exit_code = run_download(
        data_dir=data_dir,
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=True,
        api_key="test-key",
        cache_dir=cache_dir,
        fetch_csv=fake_fetch,
    )

    assert exit_code == 0
    errors_file = simfin_errors_path(data_dir, date(2026, 6, 18))
    assert errors_file.exists()
    assert "cashflow" in errors_file.read_text()


def test_run_download_fails_when_all_critical_datasets_fail(tmp_path: Path) -> None:
    data_dir = tmp_path / "lake"

    def fail_fetch(**_kwargs: object) -> Path:
        msg = "network down"
        raise OSError(msg)

    exit_code = run_download(
        data_dir=data_dir,
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=True,
        api_key="test-key",
        cache_dir=tmp_path / "cache",
        fetch_csv=lambda **kwargs: fail_fetch(**kwargs),
    )

    assert exit_code == 1


def test_simfin_errors_path_matches_spec_layout() -> None:
    path = simfin_errors_path(Path("data"), date(2026, 6, 18))
    assert path == Path("data/raw/simfin/download_runs/as_of_date=2026-06-18/errors.json")


def test_simfin_source_filename_for_industries_without_market() -> None:
    assert simfin_source_filename(dataset="industries", variant=None, market=None) == (
        "industries.csv"
    )


def test_simfin_bulk_path_for_industries() -> None:
    path = simfin_bulk_path(
        Path("data"),
        dataset="industries",
        variant=None,
        market=None,
        as_of_date=date(2026, 6, 18),
    )
    assert path.name == "industries.csv"
    assert "variant=default" in str(path)
    assert "market=us" in str(path)


def test_configure_simfin_sets_api_key_and_cache_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_sf = MagicMock()
    monkeypatch.setattr("smartwealthai.simfin_client.sf", mock_sf)
    cache_dir = tmp_path / "cache"

    configure_simfin(api_key="test-key", cache_dir=cache_dir)

    mock_sf.set_api_key.assert_called_once_with("test-key")
    mock_sf.set_data_dir.assert_called_once_with(str(cache_dir))
    assert cache_dir.is_dir()


def test_dataset_cache_path_after_configure(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    configure_simfin(api_key="test-key", cache_dir=cache_dir)

    path = dataset_cache_path(dataset="income", variant="ttm", market="us")

    assert path == cache_dir / "us-income-ttm.csv"


def test_fetch_dataset_csv_invokes_downloader_and_returns_cache_path(tmp_path: Path) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")
    downloader = MagicMock()

    result = fetch_dataset_csv(
        dataset="income",
        variant="ttm",
        market="us",
        refresh_days=7,
        download_fn=downloader,
    )

    downloader.assert_called_once_with(
        dataset="income",
        variant="ttm",
        market="us",
        refresh_days=7,
    )
    assert result == tmp_path / "cache" / "us-income-ttm.csv"


def test_fetch_dataset_csv_passes_market_for_companies(tmp_path: Path) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")
    downloader = MagicMock()

    fetch_dataset_csv(
        dataset="companies",
        variant=None,
        market="us",
        refresh_days=7,
        download_fn=downloader,
    )

    downloader.assert_called_once_with(
        dataset="companies",
        variant=None,
        market="us",
        refresh_days=7,
    )


def test_download_dataset_csv_raises_for_unknown_dataset() -> None:
    with pytest.raises(ValueError, match="Unknown SimFin dataset"):
        fetch_dataset_csv(
            dataset="not-a-dataset",
            variant=None,
            market="us",
            refresh_days=7,
        )


def test_safe_extract_zip_rejects_path_traversal(tmp_path: Path) -> None:
    zip_path = tmp_path / "evil.zip"
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("../outside.csv", "pwned")

    with pytest.raises(ValueError, match="Unsafe zip entry path"):
        safe_extract_zip(zip_path, dest_dir)

    assert not (tmp_path / "outside.csv").exists()


def test_safe_extract_zip_allows_members_under_dest(tmp_path: Path) -> None:
    zip_path = tmp_path / "bulk.zip"
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("us-income-ttm.csv", "Ticker;Revenue\nAAPL;1\n")

    safe_extract_zip(zip_path, dest_dir)

    assert (dest_dir / "us-income-ttm.csv").read_text() == "Ticker;Revenue\nAAPL;1\n"


def _stub_simfin_bulk_download(
    monkeypatch: pytest.MonkeyPatch,
    download_path: Path,
    write_payload: Callable[[Path], None] | None = None,
) -> None:
    """Point simfin download internals at a local payload writer (no network)."""

    def fake_download(*, url: str, headers: dict[str, str], download_path: str) -> None:
        del url, headers
        if write_payload is None:
            raise AssertionError("download should not run")
        write_payload(Path(download_path))

    monkeypatch.setattr(
        "smartwealthai.simfin_client._url_dataset",
        lambda **_: "http://example.test",
    )
    monkeypatch.setattr("smartwealthai.simfin_client._headers_dataset", lambda: {})
    monkeypatch.setattr(
        "smartwealthai.simfin_client._path_download_dataset",
        lambda **_: str(download_path),
    )
    monkeypatch.setattr("smartwealthai.simfin_client._download", fake_download)


def test_download_dataset_csv_skips_fresh_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")
    csv_path = dataset_cache_path(dataset="income", variant="ttm", market="us")
    csv_path.write_text("existing\n")
    now = time.time()
    os.utime(csv_path, (now, now))

    _stub_simfin_bulk_download(monkeypatch, tmp_path / "payload.zip")
    download_dataset_csv(dataset="income", variant="ttm", market="us", refresh_days=7)

    assert csv_path.read_text() == "existing\n"


def test_download_dataset_csv_extracts_zip_into_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")

    def write_zip(path: Path) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("us-income-ttm.csv", "Ticker;Revenue\nAAPL;1\n")

    _stub_simfin_bulk_download(monkeypatch, tmp_path / "payload.zip", write_zip)
    download_dataset_csv(dataset="income", variant="TTM", market="US", refresh_days=0)

    csv_path = dataset_cache_path(dataset="income", variant="ttm", market="us")
    assert csv_path.read_text() == "Ticker;Revenue\nAAPL;1\n"


def test_download_dataset_csv_moves_plain_csv_into_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")

    def write_csv(path: Path) -> None:
        path.write_text("IndustryId;Industry\n105001;Utilities\n")

    _stub_simfin_bulk_download(monkeypatch, tmp_path / "industries.csv", write_csv)
    download_dataset_csv(dataset="industries", variant=None, market=None, refresh_days=0)

    csv_path = dataset_cache_path(dataset="industries", variant=None, market=None)
    assert csv_path.read_text() == "IndustryId;Industry\n105001;Utilities\n"


def test_download_dataset_csv_rejects_zip_slip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")

    def write_evil_zip(path: Path) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../outside.csv", "pwned")

    _stub_simfin_bulk_download(monkeypatch, tmp_path / "payload.zip", write_evil_zip)
    with pytest.raises(ValueError, match="Unsafe zip entry path"):
        download_dataset_csv(dataset="income", variant="ttm", market="us", refresh_days=0)

    assert not (tmp_path / "outside.csv").exists()


def test_download_dataset_force_requests_immediate_simfin_refresh(tmp_path: Path) -> None:
    spec = DEMO_DATASETS[2]
    cache_csv = tmp_path / "us-income-ttm.csv"
    cache_csv.write_text("csv\n")
    seen: dict[str, object] = {}

    def fake_fetch(**kwargs: object) -> Path:
        seen.update(kwargs)
        return cache_csv

    download_dataset(
        spec,
        data_dir=tmp_path / "lake",
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=True,
        fetch_csv=fake_fetch,
    )

    assert seen["refresh_days"] == 0


def test_run_download_exits_1_when_api_key_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIMFIN_API_KEY", raising=False)

    exit_code = run_download(
        data_dir=tmp_path,
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=False,
    )

    assert exit_code == 1


def test_run_download_wires_default_simfin_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured: list[Path] = []

    def mock_configure(*, api_key: str, cache_dir: Path) -> None:
        configured.append(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

    def mock_fetch(
        *,
        dataset: str,
        variant: str | None,
        market: str | None,
        **_kwargs: object,
    ) -> Path:
        path = configured[0] / f"{dataset}.csv"
        path.write_text("csv\n")
        return path

    monkeypatch.setattr("smartwealthai.download_simfin.configure_simfin", mock_configure)
    monkeypatch.setattr("smartwealthai.download_simfin.fetch_dataset_csv", mock_fetch)

    exit_code = run_download(
        data_dir=tmp_path / "lake",
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=True,
        api_key="test-key",
    )

    assert exit_code == 0
    assert configured == [tmp_path / "lake" / "cache" / "simfin"]


def test_run_download_success_does_not_write_errors_file(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"

    def fake_fetch(
        *,
        dataset: str,
        variant: str | None,
        market: str | None,
        **_kwargs: object,
    ) -> Path:
        path = cache_dir / f"{dataset}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("csv\n")
        return path

    exit_code = run_download(
        data_dir=tmp_path / "lake",
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=True,
        api_key="test-key",
        cache_dir=cache_dir,
        fetch_csv=fake_fetch,
    )

    assert exit_code == 0
    assert not simfin_errors_path(tmp_path / "lake", date(2026, 6, 18)).exists()


def test_run_download_skips_all_fresh_datasets(tmp_path: Path) -> None:
    data_dir = tmp_path / "lake"
    now = time.time()
    for spec in DEMO_DATASETS:
        lake_path = simfin_bulk_path(
            data_dir,
            dataset=spec.name,
            variant=spec.variant,
            market=spec.market,
            as_of_date=date(2026, 6, 18),
        )
        lake_path.parent.mkdir(parents=True, exist_ok=True)
        lake_path.write_text("existing\n")
        os.utime(lake_path, (now, now))

    def fail_fetch(**_kwargs: object) -> Path:
        raise AssertionError("fetch should not run when all lake copies are fresh")

    exit_code = run_download(
        data_dir=data_dir,
        as_of_date=date(2026, 6, 18),
        refresh_days=7,
        force=False,
        api_key="test-key",
        cache_dir=tmp_path / "cache",
        fetch_csv=fail_fetch,
    )

    assert exit_code == 0


def test_cli_run_exits_1_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIMFIN_API_KEY", raising=False)
    assert cli_run([]) == 1


def test_cli_run_delegates_to_run_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def mock_run_download(**kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr("smartwealthai.download_simfin.run_download", mock_run_download)

    assert cli_run(["--data-dir", str(tmp_path), "--force"]) == 0
    assert seen["data_dir"] == tmp_path
    assert seen["force"] is True


def test_cli_run_passes_as_of_date_to_run_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def mock_run_download(**kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr("smartwealthai.download_simfin.run_download", mock_run_download)

    assert cli_run(["--as-of-date", "2026-06-18"]) == 0
    assert seen["as_of_date"] == date(2026, 6, 18)
