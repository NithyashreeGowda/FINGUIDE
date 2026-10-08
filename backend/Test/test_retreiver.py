import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.retreiver import FinancialRetriever


# 1. Load document
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


# 3. TEST ONLY
test_chunks = chunks[:5]


# 4. Create embeddings
embedding_model = EmbeddingModel()

embeddings = embedding_model.encode_texts(
    [chunk["text"] for chunk in test_chunks]
)


# 5. Create vector store
vector_store = VectorStore(
    dimension=len(embeddings[0])
)

vector_store.add_embeddings(
    embeddings,
    test_chunks,
)


# 6. Create retriever
retriever = FinancialRetriever(
    vector_store=vector_store,
    embedding_model=embedding_model,
)


# 7. Search
query = "Reliance financial performance and business growth"

results = retriever.retrieve(
    query=query,
    top_k=3,
)


print()
print("QUERY:")
print(query)
print()

print("RETRIEVED EVIDENCE:")
print()


for index, result in enumerate(results, start=1):
    print("=" * 70)
    print(f"RESULT {index}")
    print("=" * 70)

    print("Similarity:", result["score"])
    print("Company:", result["company"])
    print("Source:", result["source"])
    print("Date:", result["date"])
    print("Page:", result["page"])
    print("Document type:", result["document_type"])

    print()
    print("TEXT:")
    print(result["text"][:700])
    print()