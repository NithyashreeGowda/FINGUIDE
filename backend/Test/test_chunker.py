import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks


PDF_PATH = BACKEND_DIR / "data" / "financial_documents" / "Reliance-2024-25.pdf"


document = load_financial_document(
    str(PDF_PATH),
    source="Reliance Industries Limited Annual Report 2024-25",
    company="Reliance Industries Limited",
    document_type="annual_report",
    document_date="2025-03-31",
)


chunks = create_evidence_chunks(
    document["evidence"],
    chunk_size=1200,
    chunk_overlap=200,
)


print("Pages:", document["page_count"])
print("Total chunks:", len(chunks))


# ---------------------------------------------------------
# Inspect chunks from pages that previously appeared
# during retrieval.
# ---------------------------------------------------------

TARGET_PAGES = {39, 64, 80, 87, 91, 130, 135, 138, 142}


for page in sorted(TARGET_PAGES):

    page_chunks = [
        chunk
        for chunk in chunks
        if chunk["page"] == page
    ]

    print()
    print("=" * 80)
    print(f"PAGE {page} — {len(page_chunks)} CHUNK(S)")
    print("=" * 80)

    for chunk in page_chunks:

        print()
        print("-" * 80)
        print(
            f"Chunk ID: {chunk['chunk_id']} "
            f"| Chunk index: {chunk['chunk_index']}"
        )
        print("-" * 80)

        print(chunk["text"])

