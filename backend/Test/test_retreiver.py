import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.retreiver import FinancialRetriever


def test_query(retriever, query):
    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    results = retriever.retrieve(
        query=query,
        top_k=5,
        candidate_k=50,
        minimum_score=0.50,
    )

    for index, result in enumerate(results, start=1):

        print(f"\nRESULT {index}")
        print("-" * 80)

        print(f"Page: {result.get('page')}")
        print(f"FAISS similarity: {result.get('semantic_score', 0):.4f}")
        print(f"Keyword score: {result.get('keyword_score', 0):.4f}")
        print(f"Intent score: {result.get('intent_score', 0):.4f}")
        print(f"Evidence score: {result.get('evidence_score', 0):.4f}")
        print(f"Noise score: {result.get('noise_score', 0):.4f}")
        print(f"Final score: {result.get('rerank_score', 0):.4f}")

        print("\nCompany:")
        print(result.get("company"))

        print("\nSource:")
        print(result.get("source"))

        print("\nText:")
        print(result.get("text", "")[:800])


def main():

    print("Loading vector store...")

    vector_store = VectorStore(dimension=384)

    vector_store.load(
        index_path=str(BACKEND_DIR / "data" / "faiss_index.index"),
        metadata_path=str(BACKEND_DIR / "data" / "faiss_metadata.json"),
    )

    print(f"Vectors loaded: {vector_store.index.ntotal}")
    print(f"Metadata records loaded: {len(vector_store.metadata)}")

    print("\nLoading embedding model...")

    embedding_model = EmbeddingModel()

    retriever = FinancialRetriever(
        vector_store=vector_store,
        embedding_model=embedding_model,
    )

    queries = [
        "What was Reliance's revenue in FY 2024-25?",
        "What was Reliance's net profit in FY 2024-25?",
        "What was Reliance's EBITDA?",
        "What was Reliance's debt position?",
        "What was Reliance's cash flow?",
    ]

    for query in queries:
        test_query(retriever, query)


if __name__ == "__main__":
    main()