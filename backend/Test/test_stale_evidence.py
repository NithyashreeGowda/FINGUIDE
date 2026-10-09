import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.evidence_validator import validate_evidence


print("=" * 70)
print("COMPLETE STALE EVIDENCE PIPELINE TEST")
print("=" * 70)

evidence = [
    {
        "text": (
            "Reliance Industries reported revenue from operations "
            "of ₹9,80,136 crore."
        ),
        "source": "Reliance Annual Report 2020-21",
        "date": date(2021, 3, 31),
        "document_type": "official_company_report",
        "page": 100,
    }
]

claim = (
    "Reliance reported revenue from operations "
    "of ₹9,80,136 crore in FY 2020-21."
)

result = validate_evidence(
    evidence_results=evidence,
    claim=claim,
    metric="revenue from operations",
    reference_date=date(2026, 10, 8),
    source_type="official_company_report",
    freshness_period_months=12,
)

print()
print("Evidence valid:", result["evidence_valid"])
print("Overall status:", result["status"])

print()
print("SOURCE VALIDATION")
print("-" * 70)

for source in result["source_validation"]:
    print("Source:", source.get("source"))
    print("Freshness score:", source.get("freshness_score"))
    print("Fresh:", source.get("is_fresh"))

print()
print("CLAIM SUPPORT")
print("-" * 70)
print(result["claim_support"])

print()
print("CONFLICT DETECTION")
print("-" * 70)
print(result["conflict_detection"])