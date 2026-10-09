import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.retreiver import FinancialRetriever
from rag.reranker import EvidenceReranker


vector_store = VectorStore(dimension=384)

vector_store.load(
    index_path=str(BACKEND_DIR / "data" / "faiss_index.index"),
    metadata_path=str(BACKEND_DIR / "data" / "faiss_metadata.json"),
)

print("Vectors loaded:", vector_store.index.ntotal)
print("Metadata records loaded:", len(vector_store.metadata))

embedding_model = EmbeddingModel()

reranker = EvidenceReranker()

retriever = FinancialRetriever(
    vector_store=vector_store,
    embedding_model=embedding_model,
    reranker=reranker,
)

query = "What was Reliance's financial performance?"

results = retriever.retrieve(
    query=query,
    top_k=5,
    candidate_k=20,
    minimum_score=0.50,
)

print()
print("QUERY:")
print(query)

print()

for index, result in enumerate(results, start=1):

    print("=" * 70)
    print(f"RESULT {index}")
    print("=" * 70)

    print("FAISS similarity:", result["semantic_score"])
    print("Keyword score:", result["keyword_score"])
    print("Intent score:", result["intent_score"])
    print(f"Evidence score: {result['evidence_score']}")
    print("Noise score:", result["noise_score"])
    print("Final rerank score:", result["rerank_score"])

    print("Company:", result["company"])
    print("Source:", result["source"])
    print("Date:", result["date"])
    print("Page:", result["page"])
    print("Document type:", result["document_type"])

    print()
    print("TEXT:")
    print(result["text"][:700])
    print()