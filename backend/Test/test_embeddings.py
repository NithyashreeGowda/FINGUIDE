import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks
from rag.embeddings import EmbeddingModel


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


# Test with only 5 chunks first
test_chunks = chunks[:5]

texts = [
    chunk["text"]
    for chunk in test_chunks
]


embedding_model = EmbeddingModel()

embeddings = embedding_model.encode_texts(texts)


print()
print("Number of chunks:", len(texts))
print("Number of embeddings:", len(embeddings))
print("Embedding dimensions:", len(embeddings[0]))
print()
print("First embedding:")
print(embeddings[0][:10])