import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore


# 1. Load the financial document
document = load_financial_document(
    str(BACKEND_DIR / "data" / "financial_documents" / "Reliance-2024-25.pdf"),
    source="Reliance Industries Limited Annual Report 2024-25",
    company="Reliance Industries Limited",
    document_type="annual_report",
    document_date="2025-03-31",
)


# 2. Create chunks
chunks = create_evidence_chunks(
    document["evidence"],
    chunk_size=1000,
    chunk_overlap=200,
)


# 3. Use only 5 chunks for this test
test_chunks = chunks[:5]

texts = [
    chunk["text"]
    for chunk in test_chunks
]


# 4. Generate embeddings
embedding_model = EmbeddingModel()

embeddings = embedding_model.encode_texts(
    texts
)


# 5. Create vector store
vector_store = VectorStore(
    dimension=len(embeddings[0])
)


# 6. Add embeddings + metadata
vector_store.add_embeddings(
    embeddings,
    test_chunks,
)


# 7. Search
query = "Reliance financial performance and business growth"

query_embedding = embedding_model.encode_query(
    query
)


results = vector_store.search(
    query_embedding,
    top_k=3,
)


print()
print("Total vectors:", vector_store.index.ntotal)
print()
print("Search query:")
print(query)
print()


for result in results:
    print("=" * 60)
    print("Similarity score:", result["score"])
    print("Page:", result["page"])
    print("Company:", result["company"])
    print("Source:", result["source"])
    print("Date:", result["date"])
    print()
    print(result["text"][:500])
    print()