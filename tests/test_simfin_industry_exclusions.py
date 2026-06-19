"""Hermetic tests for SimFin industry exclusions reference (issue #56)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from smartwealthai.generate_simfin_industry_exclusions import cli_run
from smartwealthai.simfin_industry_exclusions import (
    EXCLUSION_COLUMNS,
    build_exclusions,
    load_exclusions,
)

# Stable SimFin IndustryId values (from industries bulk snapshot 2026-06-19).
BANK_ID = 104_002
INSURER_IDS = frozenset({104_004, 104_005, 104_006, 104_013})
UTILITY_IDS = frozenset({105_001, 105_002})


def test_reference_csv_has_stable_schema() -> None:
    df = load_exclusions()
    assert list(df.columns) == list(EXCLUSION_COLUMNS)
    assert not df.empty


def test_reference_csv_includes_known_bank_industry() -> None:
    df = load_exclusions()
    banks = df.loc[df["exclusion_reason"] == "bank", "industry_id"]
    assert BANK_ID in banks.values


def test_reference_csv_covers_insurers_and_utilities() -> None:
    df = load_exclusions()
    ids = set(df["industry_id"])
    assert INSURER_IDS <= ids
    assert UTILITY_IDS <= ids
    assert df["exclusion_reason"].isin(["bank", "insurer", "utility"]).all()


def test_build_exclusions_selects_banks_insurers_and_utilities() -> None:
    industries = pd.DataFrame(
        {
            "Industry": [
                "Banks",
                "Insurance - Life",
                "Application Software",
                "Utilities - Regulated",
            ],
            "Sector": [
                "Financial Services",
                "Financial Services",
                "Technology",
                "Utilities",
            ],
        },
        index=pd.Index([104_002, 104_004, 101_003, 105_001], name="IndustryId"),
    )

    result = build_exclusions(industries)

    assert list(result.columns) == list(EXCLUSION_COLUMNS)
    assert set(result["industry_id"]) == {104_002, 104_004, 105_001}
    assert set(result["exclusion_reason"]) == {"bank", "insurer", "utility"}


def test_cli_regenerates_exclusions_from_industries_csv(tmp_path: Path) -> None:
    industries = tmp_path / "industries.csv"
    industries.write_text(
        "IndustryId;Industry;Sector\n"
        "104002;Banks;Financial Services\n"
        "101003;Application Software;Technology\n"
        "105001;Utilities - Regulated;Utilities\n"
    )
    output = tmp_path / "exclusions.csv"

    assert cli_run(["--industries", str(industries), "--output", str(output)]) == 0

    df = pd.read_csv(output)
    assert set(df["industry_id"]) == {104_002, 105_001}
