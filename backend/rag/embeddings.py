import math

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"
EXPECTED_EMBEDDING_DIMENSION = 384


class EmbeddingModel:
    """Generates normalized vector embeddings for financial evidence."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        print(f"Loading embedding model: {model_name}")

        self.model = SentenceTransformer(model_name)

        if hasattr(self.model, "get_embedding_dimension"):
            self.embedding_dimension = self.model.get_embedding_dimension()
        elif hasattr(self.model, "get_sentence_embedding_dimension"):
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        else:
            raise AttributeError(
                "SentenceTransformer model does not expose a known embedding-dimension API."
            )

        if self.embedding_dimension != EXPECTED_EMBEDDING_DIMENSION:
            raise ValueError(
                f"Unexpected embedding dimension: {self.embedding_dimension}. "
                f"Expected: {EXPECTED_EMBEDDING_DIMENSION}"
            )

        print(
            f"Embedding model loaded successfully. Dimension: {self.embedding_dimension}"
        )

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        """Convert multiple financial evidence chunks into embeddings."""
        if not texts:
            return []

        cleaned_texts = []
        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise TypeError(f"Text at index {index} must be a string.")
            if not text.strip():
                raise ValueError(f"Text at index {index} is empty.")
            cleaned_texts.append(text.strip())

        embeddings = self.model.encode(
            cleaned_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        if isinstance(embeddings, list):
            numpy_embeddings = np.asarray(embeddings, dtype=np.float32)
        else:
            numpy_embeddings = np.asarray(embeddings, dtype=np.float32)

        if numpy_embeddings.ndim != 2:
            raise ValueError("Embeddings must be a 2D array.")
        if numpy_embeddings.shape[1] != EXPECTED_EMBEDDING_DIMENSION:
            raise ValueError(
                f"Expected {EXPECTED_EMBEDDING_DIMENSION} dimensions, "
                f"but received {numpy_embeddings.shape[1]}."
            )
        if not np.isfinite(numpy_embeddings).all():
            raise ValueError("Embeddings contain NaN or infinity values.")

        return numpy_embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        """Convert a user's financial question into an embedding."""
        if not isinstance(query, str):
            raise TypeError("Query must be a string.")
        if not query.strip():
            raise ValueError("Query cannot be empty.")

        embedding = self.model.encode(
            query.strip(),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        embedding_array = np.asarray(embedding, dtype=np.float32)
        if embedding_array.ndim != 1:
            raise ValueError("Query embedding must be one-dimensional.")
        if len(embedding_array) != EXPECTED_EMBEDDING_DIMENSION:
            raise ValueError(
                f"Expected {EXPECTED_EMBEDDING_DIMENSION} dimensions, "
                f"but received {len(embedding_array)}."
            )
        if not np.isfinite(embedding_array).all():
            raise ValueError("Query embedding contains NaN or infinity values.")

        return embedding_array.tolist()
