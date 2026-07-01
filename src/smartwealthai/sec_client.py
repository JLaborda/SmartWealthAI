"""SEC EDGAR REST client for ``companyfacts`` downloads.

Implements SEC fair-access rules:

- Identifiable ``User-Agent`` from ``SEC_IDENTITY`` env var.
- Request throttling (~8 req/s).
- Retries with exponential backoff on transient failures.

Operator guide: ``spec/guides/download-fundamentals.md``.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

SEC_DATA_URL = "https://data.sec.gov"
SEC_THROTTLE_SEC = 0.12
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3

_last_request_at = 0.0


class SecClientError(Exception):
    """Raised when a SEC request fails after retries or on permanent HTTP errors."""


def get_sec_identity() -> str:
    """Return the required SEC identity from the environment.

    Returns:
        Value of ``SEC_IDENTITY`` (format: ``"Name email@example.com"``).

    Raises:
        SecClientError: When the variable is unset or blank.
    """
    identity = os.environ.get("SEC_IDENTITY", "").strip()
    if not identity:
        msg = "SEC_IDENTITY environment variable is required (format: 'Name email@example.com')"
        raise SecClientError(msg)
    return identity


def _throttle() -> None:
    """Sleep if the previous SEC request was too recent."""
    global _last_request_at
    elapsed = time.time() - _last_request_at
    if elapsed < SEC_THROTTLE_SEC:
        time.sleep(SEC_THROTTLE_SEC - elapsed)
    _last_request_at = time.time()


def _is_transient(exc: Exception) -> bool:
    """Return True when the exception warrants a retry."""
    if isinstance(exc, requests.Timeout):
        return True
    if isinstance(exc, requests.ConnectionError):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in TRANSIENT_STATUS_CODES
    return False


def fetch_json(url: str, *, force: bool = False, cache_path: Path | None = None) -> dict:
    """Fetch JSON from SEC with throttle, optional on-disk cache, and retries.

    When ``cache_path`` exists and ``force`` is False, reads from disk without a
    network call.

    Args:
        url: Full SEC API URL.
        force: When True, ignore an existing cache file.
        cache_path: Optional path to persist the JSON response.

    Returns:
        Parsed JSON document.

    Raises:
        SecClientError: On 404 or after exhausting retries.
    """
    if cache_path is not None and cache_path.exists() and not force:
        return json.loads(cache_path.read_text())

    identity = get_sec_identity()
    headers = {
        "User-Agent": identity,
        "Accept-Encoding": "gzip, deflate",
    }

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            _throttle()
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(data))
            return data
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise SecClientError(f"SEC resource not found: {url}") from exc
            last_error = exc
            if not _is_transient(exc) or attempt == MAX_RETRIES - 1:
                break
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt == MAX_RETRIES - 1:
                break

        time.sleep(2**attempt)

    msg = f"SEC request failed after {MAX_RETRIES} attempts: {url}"
    raise SecClientError(msg) from last_error


def fetch_companyfacts(cik: str, cache_path: Path, *, force: bool = False) -> dict:
    """Download verbatim ``companyfacts`` JSON for a CIK.

    Args:
        cik: SEC issuer CIK (padded internally to 10 digits).
        cache_path: Destination path for the raw JSON snapshot.
        force: When True, re-download even if ``cache_path`` exists.

    Returns:
        Parsed ``companyfacts`` document (also written to ``cache_path`` when fetched).
    """
    cik_padded = str(cik).zfill(10)
    url = f"{SEC_DATA_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json"
    return fetch_json(url, force=force, cache_path=cache_path)
