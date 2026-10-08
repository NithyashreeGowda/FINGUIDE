import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import load_financial_document


result = load_financial_document(
    str(BACKEND_DIR / "data" / "financial_documents" / "Reliance-2024-25.pdf"),
    source="Reliance Industries Limited Annual Report 2024-25",
    company="Reliance Industries Limited",
    document_type="annual_report",
    document_date="2025-03-31",
)


print("Document:", result["file_name"])
print("Pages:", result["page_count"])
print("Company:", result["company"])
print("Document type:", result["document_type"])
print()

for evidence in result["evidence"][:2]:
    print("----- EVIDENCE -----")
    print("Page:", evidence["page"])
    print("Source:", evidence["source"])
    print("Date:", evidence["date"])
    print("Company:", evidence["company"])
    print("Type:", evidence["document_type"])
    print("Text:")
    print(evidence["text"][:500])
    print()