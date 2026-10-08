from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.reranker import EvidenceReranker


class FinancialRetriever:

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
        reranker: EvidenceReranker | None = None,
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.reranker = reranker or EvidenceReranker()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
        minimum_score: float = 0.50,
    ) -> list[dict]:

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0.")

        if candidate_k < top_k:
            candidate_k = top_k

        if minimum_score < -1.0 or minimum_score > 1.0:
            raise ValueError(
                "minimum_score must be between -1.0 and 1.0."
            )

        query_embedding = self.embedding_model.encode_query(query)

        candidates = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=candidate_k,
        )

        filtered_candidates = [
            result
            for result in candidates
            if result.get("score", 0.0) >= minimum_score
        ]

        results = self.reranker.rerank(
            query=query,
            candidates=filtered_candidates,
            top_k=top_k,
        )

        return results