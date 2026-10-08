from pathlib import Path

from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore


BACKEND_DIR = Path(__file__).resolve().parent
PDF_PATH = BACKEND_DIR / "data" / "financial_documents" / "Reliance-2024-25.pdf"

SOURCE = "Reliance Industries Limited Annual Report 2024-25"
COMPANY = "Reliance Industries Limited"
DOCUMENT_TYPE = "annual_report"
DOCUMENT_DATE = "2025-03-31"


def main():
    print("Loading financial document...")

    document = load_financial_document(
        str(PDF_PATH),
        source=SOURCE,
        company=COMPANY,
        document_type=DOCUMENT_TYPE,
        document_date=DOCUMENT_DATE,
    )

    print(f"Pages extracted: {document['page_count']}")

    print("\nCreating chunks...")

    chunks = create_evidence_chunks(
        document["evidence"],
        chunk_size=1000,
        chunk_overlap=200,
    )

    print(f"Total chunks: {len(chunks)}")

    print("\nLoading embedding model...")

    embedding_model = EmbeddingModel()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print("\nGenerating embeddings...")

    embeddings = embedding_model.encode_texts(
        texts
    )

    print(
        f"Generated {len(embeddings)} embeddings."
    )

    print("\nCreating FAISS vector store...")

    vector_store = VectorStore(
        dimension=len(embeddings[0])
    )

    vector_store.add_embeddings(
        embeddings,
        chunks,
    )

    print(
        f"Vectors stored: {vector_store.index.ntotal}"
    )

    print("\nSaving vector store...")

    vector_store.save(
        index_path=str(BACKEND_DIR / "data" / "faiss_index.index"),
        metadata_path=str(BACKEND_DIR / "data" / "faiss_metadata.json"),
    )

    print("\nVector store built successfully.")
    print("FAISS index: data/faiss_index.index")
    print("Metadata: data/faiss_metadata.json")


if __name__ == "__main__":
    main()