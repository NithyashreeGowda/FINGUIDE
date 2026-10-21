import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.evidence_validator import validate_evidence


def main():

    evidence_results = [
        {
            "text": (
                "Consolidated Statement of Profit and Loss. "
                "Revenue from operations for the year ended "
                "31 March 2025 was ₹9,80,136 crore."
            ),
            "source": "Reliance Industries Limited Annual Report 2024-25",
            "company": "Reliance Industries Limited",
            "document_type": "annual_report",
            "date": "2025-03-31",
            "page": 100,
        }
    ]

    claim = (
        "Reliance reported revenue from operations "
        "of ₹9,80,136 crore in FY 2024-25."
    )

    result = validate_evidence(
        evidence_results=evidence_results,
        claim=claim,
        metric="revenue from operations",
        reference_date="2025-04-01",
        source_type="official_company_report",
        freshness_period_months=24,
    )

    print("=" * 70)
    print("COMPLETE EVIDENCE VALIDATION PIPELINE")
    print("=" * 70)

    print(f"\nEvidence valid: {result['evidence_valid']}")
    print(f"Overall status: {result['status']}")

    print("\nSOURCE VALIDATION")
    print("-" * 70)

    for item in result["source_validation"]:
        print(f"Source: {item['source']}")
        print(f"Page: {item['page']}")
        print(
            f"Credibility: "
            f"{item['source_credibility_score']}"
        )
        print(
            f"Freshness: "
            f"{item['freshness_score']}"
        )
        print(
            f"Fresh: "
            f"{item['is_fresh']}"
        )

    print("\nCLAIM SUPPORT")
    print("-" * 70)

    print(result["claim_support"])

    print("\nCONFLICT DETECTION")
    print("-" * 70)

    print(result["conflict_detection"])


if __name__ == "__main__":
    main()