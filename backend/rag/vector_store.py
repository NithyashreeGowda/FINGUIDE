
import json
from pathlib import Path

import faiss
import numpy as np


class VectorStore:
    """
    Stores financial evidence embeddings using FAISS
    and maintains their corresponding metadata.
    """

    def __init__(self, dimension: int = 384):
        if dimension <= 0:
            raise ValueError("Embedding dimension must be positive.")

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata = []

    def add_embeddings(
        self,
        embeddings: list[list[float]],
        metadata: list[dict],
    ):
        """
        Add embedding vectors and their metadata to FAISS.
        """

        if len(embeddings) != len(metadata):
            raise ValueError(
                "Number of embeddings must match number of metadata records."
            )

        if not embeddings:
            return

        for index, record in enumerate(metadata):
            if not isinstance(record, dict):
                raise TypeError(
                    f"Metadata at position {index} must be a dictionary."
                )

        vectors = np.asarray(embeddings, dtype=np.float32)

        if vectors.ndim != 2:
            raise ValueError(
                "Embeddings must be a 2D array."
            )

        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Expected embedding dimension {self.dimension}, "
                f"got {vectors.shape[1]}."
            )

        if not np.isfinite(vectors).all():
            raise ValueError(
                "Embeddings contain invalid numeric values."
            )

        self.index.add(vectors)
        self.metadata.extend(metadata)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve the most relevant evidence chunks
        using FAISS similarity search.
        """

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if self.index.ntotal != len(self.metadata):
            raise ValueError(
                "FAISS index and metadata count do not match."
            )

        if self.index.ntotal == 0:
            return []

        query_vector = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        if query_vector.ndim != 1:
            raise ValueError(
                "Query embedding must be a one-dimensional vector."
            )

        if len(query_vector) != self.dimension:
            raise ValueError(
                f"Expected query dimension {self.dimension}, "
                f"got {len(query_vector)}."
            )

        if not np.isfinite(query_vector).all():
            raise ValueError(
                "Query embedding contains invalid numeric values."
            )

        query_vector = query_vector.reshape(1, -1)

        scores, indices = self.index.search(
            query_vector,
            min(top_k, self.index.ntotal),
        )

        results = []

        for score, index in zip(scores[0], indices[0]):

            if index == -1:
                continue

            result = self.metadata[index].copy()
            result["score"] = float(score)

            results.append(result)

        return results

    def save(
        self,
        index_path: str = "data/faiss_index.index",
        metadata_path: str = "data/faiss_metadata.json",
    ):
        """
        Save the FAISS index and metadata to disk.
        """

        if self.index.ntotal != len(self.metadata):
            raise ValueError(
                "FAISS index and metadata count do not match."
            )

        index_file = Path(index_path)
        metadata_file = Path(metadata_path)

        index_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        metadata_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        faiss.write_index(
            self.index,
            str(index_file),
        )

        with open(
            metadata_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                self.metadata,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print(f"FAISS index saved: {index_file}")
        print(f"Metadata saved: {metadata_file}")
        print(f"Total vectors saved: {self.index.ntotal}")

    def load(
        self,
        index_path: str = "data/faiss_index.index",
        metadata_path: str = "data/faiss_metadata.json",
    ):
        """
        Load a previously saved FAISS index and metadata.
        """

        index_file = Path(index_path)
        metadata_file = Path(metadata_path)

        if not index_file.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}"
            )

        if not metadata_file.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {metadata_path}"
            )

        loaded_index = faiss.read_index(
            str(index_file)
        )

        if loaded_index.d != self.dimension:
            raise ValueError(
                f"Loaded index dimension is {loaded_index.d}, "
                f"but expected {self.dimension}."
            )

        with open(
            metadata_file,
            "r",
            encoding="utf-8",
        ) as file:

            loaded_metadata = json.load(file)

        if not isinstance(loaded_metadata, list):
            raise ValueError(
                "Metadata file must contain a list."
            )

        if not all(isinstance(item, dict) for item in loaded_metadata):
            raise ValueError(
                "Every metadata record must be a dictionary."
            )

        if loaded_index.ntotal != len(loaded_metadata):
            raise ValueError(
                "FAISS index and metadata count do not match."
            )

        self.index = loaded_index
        self.metadata = loaded_metadata

        print("FAISS index loaded successfully.")
        print(f"Total vectors loaded: {self.index.ntotal}")

    def get_total_vectors(self) -> int:
        """
        Return the total number of stored embeddings.
        """

        return self.index.ntotal
