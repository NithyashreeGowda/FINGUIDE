import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.evidence_validator import calculate_claim_support


def main():

    claim = (
       "Reliance reported a net profit of ₹2,50,000 crore in FY 2024-25."
    )

    evidence = """
    Consolidated Statement of Profit and Loss.
    Revenue from operations for the year ended
    31 March 2025 was ₹9,80,136 crore.
    """

    result = calculate_claim_support(
        claim=claim,
        evidence_text=evidence,
    )

    print("=" * 70)
    print("CLAIM / EVIDENCE SUPPORT TEST")
    print("=" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()