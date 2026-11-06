import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from company_master import (
    NIFTY500_SOURCE_URL,
    Nifty500CompanyMaster,
    parse_nifty500_constituents,
)


CSV_CONTENT = (
    "Company Name,Industry,Symbol,Series,ISIN Code\n"
    "Alpha Ltd.,Technology,ALPHA,EQ,INE000A01000\n"
    "Beta Ltd.,Healthcare,BETA,BE,\n"
).encode("utf-8")
VERIFIED_AT = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def test_parser_preserves_official_fields_and_marks_unavailable_unknown():
    parsed = parse_nifty500_constituents(CSV_CONTENT, verified_at=VERIFIED_AT)

    assert parsed["constituent_count"] == 2
    assert parsed["source_url"] == NIFTY500_SOURCE_URL
    assert parsed["companies"][0]["symbol"] == "ALPHA"
    assert parsed["companies"][0]["isin"] == "INE000A01000"
    assert parsed["companies"][0]["industry"] == "Technology"
    assert parsed["companies"][0]["sector"] is None
    assert parsed["companies"][0]["cin"] is None
    assert parsed["companies"][0]["official_website"] is None
    assert parsed["companies"][0]["index_memberships"] == ["NIFTY 500"]
    assert parsed["companies"][0]["source_verified_at"] == VERIFIED_AT.isoformat()
    assert parsed["companies"][1]["isin"] is None


def test_parser_rejects_non_official_source_and_duplicate_symbols():
    with pytest.raises(ValueError, match="official Nifty Indices"):
        parse_nifty500_constituents(
            CSV_CONTENT,
            source_url="https://example.com/nifty500.csv",
            verified_at=VERIFIED_AT,
        )

    duplicate_csv = (
        "Company Name,Industry,Symbol,Series,ISIN Code\n"
        "Alpha Ltd.,Technology,ALPHA,EQ,INE000A01000\n"
        "Another Alpha Ltd.,Technology,ALPHA,EQ,INE000B01000\n"
    ).encode("utf-8")
    with pytest.raises(ValueError, match="Duplicate NIFTY 500 symbol"):
        parse_nifty500_constituents(duplicate_csv, verified_at=VERIFIED_AT)


def test_master_refresh_is_repeatable_and_keeps_source_snapshot(tmp_path):
    master_path = tmp_path / "master.json"
    source_path = tmp_path / "constituents.csv"
    master = Nifty500CompanyMaster(
        master_path=master_path,
        constituents_path=source_path,
    )

    first = master.refresh_from_csv(CSV_CONTENT, verified_at=VERIFIED_AT)
    second = master.refresh_from_csv(CSV_CONTENT, verified_at=VERIFIED_AT)

    assert first["constituent_count"] == second["constituent_count"] == 2
    assert first["source_sha256"] == second["source_sha256"]
    assert source_path.read_bytes() == CSV_CONTENT
    assert master.get_company_by_symbol("alpha")["name"] == "Alpha Ltd."
    assert master.summary()["verified_count"] == 2


def test_invalid_refresh_does_not_replace_existing_master(tmp_path):
    master_path = tmp_path / "master.json"
    source_path = tmp_path / "constituents.csv"
    master = Nifty500CompanyMaster(
        master_path=master_path,
        constituents_path=source_path,
    )
    master.refresh_from_csv(CSV_CONTENT, verified_at=VERIFIED_AT)
    previous_master = master_path.read_bytes()
    previous_source = source_path.read_bytes()

    with pytest.raises(ValueError, match="missing required columns"):
        master.refresh_from_csv(b"<html>not a CSV file</html>", verified_at=VERIFIED_AT)

    assert master_path.read_bytes() == previous_master
    assert source_path.read_bytes() == previous_source
