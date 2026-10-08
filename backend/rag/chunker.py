from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to split.
        chunk_size: Maximum approximate size of each chunk.
        chunk_overlap: Number of characters shared between chunks.

    Returns:
        List of text chunks.
    """

    if not text or not text.strip():
        return []

    text = text.strip()

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size."
        )

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - chunk_overlap

    return chunks


def create_evidence_chunks(
    evidence_pages: list[dict[str, Any]],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """
    Convert page-level financial evidence into RAG-ready chunks.

    Metadata from the original page is preserved for every chunk.
    """

    all_chunks = []

    for page_data in evidence_pages:
        text = page_data.get("text", "")

        chunks = chunk_text(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk_index, chunk in enumerate(chunks):
            all_chunks.append(
                {
                    "text": chunk,
                    "source": page_data.get("source"),
                    "date": page_data.get("date"),
                    "company": page_data.get("company"),
                    "document_type": page_data.get("document_type"),
                    "page": page_data.get("page"),
                    "file_name": page_data.get("file_name"),
                    "chunk_index": chunk_index,
                }
            )

    return all_chunks