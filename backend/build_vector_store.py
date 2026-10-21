
from pathlib import Path

from rag.document_loader import load_financial_document
from rag.chunker import create_evidence_chunks
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore


BACKEND_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BACKEND_DIR / "data" / "financial_documents"
INDEX_PATH = BACKEND_DIR / "data" / "faiss_index.index"
METADATA_PATH = BACKEND_DIR / "data" / "faiss_metadata.json"


# Add each PDF here with its correct metadata.
# Dates should be the report/publication date, not the download date.
DOCUMENTS = [
    {
        "file_name": "Reliance-2024-25.pdf",
        "source": "Reliance Industries Limited Annual Report 2024-25",
        "company": "Reliance Industries Limited",
        "document_type": "annual_report",
        "document_date": "2025-03-31",
    },

    # Example for another PDF:
    # {
    #     "file_name": "company-quarterly-results.pdf",
    #     "source": "Company Quarterly Financial Results",
    #     "company": "Company Name",
    #     "document_type": "quarterly_results",
    #     "document_date": "2026-06-30",
    # },
]


def main():
    all_chunks = []
    failed_documents = []

    print("Starting multi-document ingestion...")
    print(f"Documents folder: {DOCUMENTS_DIR}")

    for config in DOCUMENTS:
        pdf_path = DOCUMENTS_DIR / config["file_name"]

        print(f"\nProcessing: {config['file_name']}")

        try:
            if not pdf_path.is_file():
                raise FileNotFoundError(
                    f"PDF not found: {pdf_path}"
                )

            document = load_financial_document(
                str(pdf_path),
                source=config["source"],
                company=config["company"],
                document_type=config["document_type"],
                document_date=config["document_date"],
            )

            chunks = create_evidence_chunks(
                document["evidence"],
                chunk_size=1000,
                chunk_overlap=200,
            )

            if not chunks:
                raise ValueError("No evidence chunks were created.")

            # Ensure the document filename is preserved in every chunk.
            for chunk in chunks:
                chunk.setdefault(
                    "file_name",
                    config["file_name"],
                )

            all_chunks.extend(chunks)

            print(f"Pages extracted: {document['page_count']}")
            print(f"Chunks created: {len(chunks)}")

        except Exception as exc:
            failed_documents.append(
                (config["file_name"], str(exc))
            )
            print(f"ERROR: {exc}")

    if not all_chunks:
        raise RuntimeError(
            "No chunks were created. The existing saved index has not "
            "been intentionally overwritten by this script."
        )

    print(f"\nTotal chunks across documents: {len(all_chunks)}")

    print("\nLoading embedding model...")
    embedding_model = EmbeddingModel()

    texts = [chunk["text"] for chunk in all_chunks]

    print("Generating embeddings...")
    embeddings = embedding_model.encode_texts(texts)

    if len(embeddings) != len(all_chunks):
        raise ValueError(
            "Embedding count does not match chunk count."
        )

    if len(embeddings) == 0:
        raise ValueError("No embeddings were generated.")

    print(f"Embeddings generated: {len(embeddings)}")

    print("\nBuilding a fresh FAISS index...")
    vector_store = VectorStore(
        dimension=len(embeddings[0])
    )

    vector_store.add_embeddings(
        embeddings,
        all_chunks,
    )

    if vector_store.index.ntotal != len(vector_store.metadata):
        raise ValueError(
            "FAISS vector count does not match metadata count."
        )

    print("Saving vector store...")
    vector_store.save(
        index_path=str(INDEX_PATH),
        metadata_path=str(METADATA_PATH),
    )

    print("\nVector store built successfully.")
    print(f"PDFs configured: {len(DOCUMENTS)}")
    print(f"Chunks indexed: {vector_store.index.ntotal}")
    print(f"FAISS index: {INDEX_PATH}")
    print(f"Metadata: {METADATA_PATH}")

    if failed_documents:
        print("\nWARNING: Some PDFs were skipped:")
        for file_name, error in failed_documents:
            print(f"- {file_name}: {error}")

    print("\nImportant: The index contains successfully processed PDFs only.")


if __name__ == "__main__":
    main()
