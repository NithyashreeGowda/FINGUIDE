import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import extract_text_from_file


def test_xbrl_loader_extracts_facts(tmp_path):
    xbrl_path = tmp_path / "reliance.xbrl"
    xbrl_path.write_text(
        """<?xml version=\"1.0\"?>
        <xbrli:xbrl xmlns:xbrli=\"http://www.xbrl.org/2003/instance\"
                    xmlns:dei=\"http://example.com/dei\"
                    xmlns:us-gaap=\"http://example.com/us-gaap\">
            <dei:EntityRegistrantName contextRef=\"c1\">Reliance Industries Limited</dei:EntityRegistrantName>
            <us-gaap:Revenues contextRef=\"c1\" unitRef=\"USD\" decimals=\"0\">980136</us-gaap:Revenues>
            <context id=\"c1\">
                <entity><identifier scheme=\"http://example.com\">RIL</identifier></entity>
                <period><startDate>2024-04-01</startDate><endDate>2025-03-31</endDate></period>
            </context>
        </xbrli:xbrl>
        """,
        encoding="utf-8",
    )

    text = extract_text_from_file(xbrl_path)

    assert "EntityRegistrantName: Reliance Industries Limited" in text
    assert "Revenues: 980136" in text or "Revenues contextRef: c1" in text
