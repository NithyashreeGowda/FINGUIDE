import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks


document = load_financial_document(
    str(BACKEND_DIR / "data" / "financial_documents" / "Reliance-2024-25.pdf"),
    source="Reliance Industries Limited Annual Report 2024-25",
    company="Reliance Industries Limited",
    document_type="annual_report",
    document_date="2025-03-31",
)


chunks = create_evidence_chunks(
    document["evidence"],
    chunk_size=1000,
    chunk_overlap=200,
)


print("Total pages:", document["page_count"])
print("Total chunks:", len(chunks))
print()


for chunk in chunks[:3]:
    print("=" * 60)
    print("Chunk index:", chunk["chunk_index"])
    print("Page:", chunk["page"])
    print("Company:", chunk["company"])
    print("Source:", chunk["source"])
    print("Date:", chunk["date"])
    print("Document type:", chunk["document_type"])
    print()
    print(chunk["text"][:500])
    print()