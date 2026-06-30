"""Universe preset loading for fundamentals download.

Universe CSVs live under ``data/reference/universes/`` and are versioned in git. Each row
maps a ``ticker`` (for edgartools) to a fixed ``cik`` (for SEC ``companyfacts``).

See ``data/reference/universes/README.md`` for file format and maintenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

UNIVERSE_PRESETS: dict[str, Path] = {
    "dow30": REPO_ROOT / "data" / "reference" / "universes" / "dow30.csv",
}
"""Named universes resolved to versioned CSV paths."""


@dataclass(frozen=True)
class UniverseEntry:
    """One issuer in a download universe."""

    ticker: str
    cik: str


def resolve_universe_file(universe: str | None, universe_file: Path | None) -> Path:
    """Resolve the CSV path from a preset name or explicit file.

    Args:
        universe: Preset key (e.g. ``"dow30"``). Ignored when ``universe_file`` is set.
        universe_file: Explicit CSV path.

    Returns:
        Path to the universe CSV.

    Raises:
        ValueError: When neither argument is provided or preset is unknown.
    """
    if universe_file is not None:
        return universe_file
    if universe is None:
        msg = "Provide --universe or --universe-file"
        raise ValueError(msg)
    try:
        return UNIVERSE_PRESETS[universe]
    except KeyError as exc:
        known = ", ".join(sorted(UNIVERSE_PRESETS))
        msg = f"Unknown universe preset '{universe}'. Known presets: {known}"
        raise ValueError(msg) from exc


def load_universe(
    universe: str | None = None,
    universe_file: Path | None = None,
) -> list[UniverseEntry]:
    """Load ticker/CIK rows from a preset or explicit CSV path.

    Args:
        universe: Preset name passed to :func:`resolve_universe_file`.
        universe_file: Optional explicit CSV path.

    Returns:
        Parsed universe entries with normalized ticker (upper) and CIK (10-digit).

    Raises:
        FileNotFoundError: When the resolved CSV does not exist.
        ValueError: When required columns are missing.
    """
    path = resolve_universe_file(universe, universe_file)
    if not path.exists():
        msg = f"Universe file not found: {path}"
        raise FileNotFoundError(msg)

    frame = pd.read_csv(path, dtype={"ticker": "string", "cik": "string"})
    required = {"ticker", "cik"}
    missing = required - set(frame.columns)
    if missing:
        msg = f"Universe file missing columns {sorted(missing)}: {path}"
        raise ValueError(msg)

    entries: list[UniverseEntry] = []
    for row in frame.itertuples(index=False):
        ticker = str(row.ticker).strip().upper()
        cik = str(row.cik).strip().zfill(10)
        entries.append(UniverseEntry(ticker=ticker, cik=cik))
    return entries
