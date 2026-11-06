import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.retreiver import FinancialRetriever


def _build_retriever():
    vector_store = VectorStore(dimension=384)
    vector_store.load(
        index_path=str(BACKEND_DIR / "data" / "faiss_index.index"),
        metadata_path=str(BACKEND_DIR / "data" / "faiss_metadata.json"),
    )
    embedding_model = EmbeddingModel()
    return FinancialRetriever(
        vector_store=vector_store,
        embedding_model=embedding_model,
    )


def test_retriever_returns_results_for_financial_query():
    retriever = _build_retriever()
    query = "What was Reliance's financial performance?"

    results = retriever.retrieve(
        query=query,
        top_k=5,
        candidate_k=20,
        minimum_score=0.50,
    )

    assert results, "retriever should return at least one relevant chunk for the sample query"
    assert isinstance(results[0].get("text"), str)
    assert results[0].get("company")


if __name__ == "__main__":
    test_retriever_returns_results_for_financial_query()
    print("retriever smoke test passed")