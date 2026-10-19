"""Stage official Kaggle competition extracts into local raw dirs (#151).

No network: operates on an already-downloaded zip or directory. Downstream
application-mart joins (Home Credit multi-table) are out of scope here (#152).
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StageCompetitionExtractResult:
    """Files staged under a credit raw competition directory."""

    dest_dir: Path
    staged_names: tuple[str, ...]
    source_path: Path


def stage_competition_extract(
    source: Path,
    dest_dir: Path,
) -> StageCompetitionExtractResult:
    """Copy or unzip ``source`` into ``dest_dir`` (created if needed).

    Parameters
    ----------
    source:
        A ``.zip`` archive or a directory of already-extracted competition files.
    dest_dir:
        Target raw layout directory (e.g. ``data/credit/raw/home_credit``).
    """
    source = Path(source)
    dest_dir = Path(dest_dir)
    if not source.exists():
        raise FileNotFoundError(f"Competition extract source not found: {source}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    if source.is_file() and source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf:
            zf.extractall(dest_dir)
    elif source.is_dir():
        for child in source.iterdir():
            target = dest_dir / child.name
            if child.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
    else:
        raise ValueError(f"source must be a .zip file or a directory, got: {source}")

    staged = tuple(sorted(p.name for p in dest_dir.rglob("*") if p.is_file()))
    return StageCompetitionExtractResult(
        dest_dir=dest_dir,
        staged_names=staged,
        source_path=source,
    )
