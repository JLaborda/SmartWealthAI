"""Public-interface tests for staging competition extracts (#151)."""

from __future__ import annotations

import zipfile
from pathlib import Path


def _make_zip(path: Path, members: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, body in members.items():
            zf.writestr(name, body)
    return path


def test_stage_competition_extract_unzips_into_dest_layout(tmp_path: Path) -> None:
    """A competition zip lands as files under the destination raw directory."""
    from credit.competition_raw import stage_competition_extract

    zip_path = _make_zip(
        tmp_path / "home-credit-default-risk.zip",
        {
            "application_train.csv": "SK_ID_CURR,TARGET\n1,0\n",
            "bureau.csv": "SK_ID_CURR,SK_ID_BUREAU\n1,10\n",
        },
    )
    dest = tmp_path / "raw" / "home_credit"

    result = stage_competition_extract(zip_path, dest)

    assert result.dest_dir == dest
    assert (dest / "application_train.csv").is_file()
    assert (dest / "bureau.csv").is_file()
    assert set(result.staged_names) >= {"application_train.csv", "bureau.csv"}


def test_stage_competition_extract_copies_directory_contents(tmp_path: Path) -> None:
    """An already-extracted directory is copied into the destination raw layout."""
    from credit.competition_raw import stage_competition_extract

    source = tmp_path / "downloaded"
    source.mkdir()
    (source / "train_labels.csv").write_text("customer_ID,target\nx,1\n", encoding="utf-8")
    dest = tmp_path / "raw" / "amex"

    result = stage_competition_extract(source, dest)

    assert (dest / "train_labels.csv").is_file()
    assert "train_labels.csv" in result.staged_names


def test_stage_competition_extract_copies_nested_dir_and_replaces(tmp_path: Path) -> None:
    """Nested source dirs are copied, replacing a stale directory at the dest."""
    from credit.competition_raw import stage_competition_extract

    source = tmp_path / "downloaded"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "train_data.csv").write_text("customer_ID\nx\n", encoding="utf-8")
    (source / "fresh").mkdir()
    (source / "fresh" / "labels.csv").write_text("customer_ID,target\nx,1\n", encoding="utf-8")
    (source / "train_labels.csv").write_text("customer_ID,target\nx,1\n", encoding="utf-8")

    dest = tmp_path / "raw" / "amex"
    stale = dest / "nested"
    stale.mkdir(parents=True)
    (stale / "stale.txt").write_text("old", encoding="utf-8")

    result = stage_competition_extract(source, dest)

    assert (dest / "nested" / "train_data.csv").is_file()
    assert not (dest / "nested" / "stale.txt").exists()
    assert (dest / "fresh" / "labels.csv").is_file()
    assert (dest / "train_labels.csv").is_file()
    assert {"train_data.csv", "labels.csv", "train_labels.csv"} <= set(result.staged_names)


def test_stage_competition_extract_requires_existing_source(tmp_path: Path) -> None:
    """A missing zip or directory is an explicit FileNotFoundError."""
    from credit.competition_raw import stage_competition_extract

    missing = tmp_path / "no-such.zip"
    try:
        stage_competition_extract(missing, tmp_path / "dest")
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError as exc:
        assert "no-such.zip" in str(exc)


def test_stage_competition_extract_rejects_non_zip_file(tmp_path: Path) -> None:
    """A plain file is neither a zip archive nor an extracted directory."""
    from credit.competition_raw import stage_competition_extract

    source = tmp_path / "notes.txt"
    source.write_text("not a zip", encoding="utf-8")
    try:
        stage_competition_extract(source, tmp_path / "dest")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "zip" in str(exc)
