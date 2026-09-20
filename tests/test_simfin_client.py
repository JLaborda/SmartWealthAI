"""Hermetic tests for SimFin cache refresh in ``download_dataset_csv``.

Complements lake-level skip tests in ``test_download_simfin.py``. Network is
stubbed; live SimFin calls stay out of PR CI.
"""

from __future__ import annotations

import os
import time
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from smartwealthai.simfin_client import (
    configure_simfin,
    dataset_cache_path,
    download_dataset_csv,
)


def _stub_simfin_download(
    monkeypatch: pytest.MonkeyPatch,
    download_path: Path,
    write_payload: Callable[[Path], None],
) -> list[str]:
    """Replace simfin download internals with a local writer. Returns call log."""
    calls: list[str] = []

    def fake_download(*, url: str, headers: dict[str, str], download_path: str) -> None:
        del url, headers
        calls.append(download_path)
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
    return calls


def _write_income_zip(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("us-income-ttm.csv", body)


def test_download_dataset_csv_redownloads_stale_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")
    csv_path = dataset_cache_path(dataset="income", variant="ttm", market="us")
    csv_path.write_text("stale\n")
    now = time.time()
    os.utime(csv_path, (now - 8 * 86400, now - 8 * 86400))

    calls = _stub_simfin_download(
        monkeypatch,
        tmp_path / "payload.zip",
        lambda path: _write_income_zip(path, "Ticker;Revenue\nAAPL;1\n"),
    )

    download_dataset_csv(dataset="income", variant="ttm", market="us", refresh_days=7)

    assert calls
    assert csv_path.read_text() == "Ticker;Revenue\nAAPL;1\n"


def test_download_dataset_csv_downloads_when_cache_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_simfin(api_key="test-key", cache_dir=tmp_path / "cache")
    csv_path = dataset_cache_path(dataset="income", variant="ttm", market="us")
    assert not csv_path.exists()

    calls = _stub_simfin_download(
        monkeypatch,
        tmp_path / "payload.zip",
        lambda path: _write_income_zip(path, "Ticker;Revenue\nMSFT;2\n"),
    )

    download_dataset_csv(dataset="income", variant="ttm", market="us", refresh_days=7)

    assert calls
    assert csv_path.read_text() == "Ticker;Revenue\nMSFT;2\n"
