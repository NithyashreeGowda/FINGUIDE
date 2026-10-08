from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore


class FinancialRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve the most relevant financial evidence
        for a user query.
        """

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        query_embedding = self.embedding_model.encode_query(
            query
        )

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        return results