import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.evidence_validator import detect_evidence_conflicts


def main():

    evidence_results = [
        {
            "text": (
                "Revenue from operations for FY 2024-25 "
                "was ₹9,80,136 crore."
            ),
            "source": "Reliance Annual Report 2024-25",
            "page": 100,
            "date": "2025-03-31",
            "company": "Reliance Industries Limited",
        },
        {
            "text": (
                "Revenue from operations for FY 2024-25 "
                "was ₹8,50,000 crore."
            ),
            "source": "Other Financial Report",
            "page": 25,
            "date": "2025-03-31",
            "company": "Reliance Industries Limited",
        },
    ]

    result = detect_evidence_conflicts(
        evidence_results=evidence_results,
        metric="revenue from operations",
    )

    print("=" * 70)
    print("EVIDENCE CONFLICT DETECTION TEST")
    print("=" * 70)

    print(f"Has conflict: {result['has_conflict']}")
    print(f"Status: {result['status']}")
    print(f"Values: {result['values']}")

    print("\nConflicting evidence:")

    for item in result["conflicting_evidence"]:
        print("-" * 50)
        print(f"Value: {item['value']}")
        print(f"Source: {item['source']}")
        print(f"Page: {item['page']}")
        print(f"Date: {item['date']}")


if __name__ == "__main__":
    main()