import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.evidence_validator import validate_evidence


def test_unverified_source_is_not_reported_as_valid_evidence():
    result = validate_evidence(
        evidence_results=[{
            "text": "Revenue from operations was 100 crore.",
            "source": "Local annual report copy",
            "date": "2026-03-01",
            "page": 1,
            "verification_status": "unverified",
        }],
        reference_date="2026-03-15",
        freshness_period_months=12,
    )

    assert result["evidence_valid"] is False
    assert result["status"] == "UNVERIFIED_SOURCE"
    assert result["source_validation"][0]["source_credibility_score"] == 0.0
    assert result["source_validation"][0]["source_verified"] is False


def test_verified_source_can_pass_source_verification():
    result = validate_evidence(
        evidence_results=[{
            "text": "Revenue from operations was 100 crore.",
            "source": "Verified annual report",
            "date": "2026-03-01",
            "page": 1,
            "verification_status": "verified",
        }],
        reference_date="2026-03-15",
        freshness_period_months=12,
    )

    assert result["evidence_valid"] is True
    assert result["status"] == "VALID"
    assert result["source_validation"][0]["source_credibility_score"] == 1.0
