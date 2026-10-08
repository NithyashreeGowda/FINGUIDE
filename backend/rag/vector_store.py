import json
from pathlib import Path

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata = []

    def add_embeddings(
        self,
        embeddings: list[list[float]],
        metadata: list[dict],
    ):
        """
        Add embeddings and their corresponding metadata
        to the FAISS vector store.
        """

        if len(embeddings) != len(metadata):
            raise ValueError(
                "Number of embeddings must match number of metadata records."
            )

        if not embeddings:
            return

        vectors = np.array(
            embeddings,
            dtype=np.float32,
        )

        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Expected embedding dimension {self.dimension}, "
                f"got {vectors.shape[1]}."
            )

        self.index.add(vectors)
        self.metadata.extend(metadata)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Search for the most semantically similar chunks.
        """

        if self.index.ntotal == 0:
            return []

        query_vector = np.array(
            [query_embedding],
            dtype=np.float32,
        )

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
        Save FAISS index and metadata to disk.
        """

        index_file = Path(index_path)
        metadata_file = Path(metadata_path)

        index_file.parent.mkdir(
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

        self.index = faiss.read_index(
            str(index_file)
        )

        with open(
            metadata_file,
            "r",
            encoding="utf-8",
        ) as file:
            self.metadata = json.load(file)