from typing import Any
import re


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text while preserving useful structure.
    """

    if not text:
        return ""

    # Normalize whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove repeated page-number/footer patterns.
    text = re.sub(
        r"\n\d+\s+Reliance Industries Limited.*?(?=\n|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def split_into_blocks(text: str) -> list[str]:
    """
    Split text into logical blocks using blank lines.

    This preserves paragraphs and table-related blocks better
    than blindly slicing every N characters.
    """

    text = clean_text(text)

    if not text:
        return []

    raw_blocks = re.split(r"\n\s*\n", text)

    blocks = []

    for block in raw_blocks:
        block = block.strip()

        if not block:
            continue

        blocks.append(block)

    return blocks


def combine_blocks(
    blocks: list[str],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Combine logical blocks into chunks while preserving block boundaries.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size."
        )

    if not blocks:
        return []

    chunks = []
    current_blocks = []
    current_length = 0

    for block in blocks:

        block_length = len(block)

        # If adding the block would exceed the target,
        # finalize the current chunk first.
        if (
            current_blocks
            and current_length + block_length + 2 > chunk_size
        ):
            chunks.append(
                "\n\n".join(current_blocks).strip()
            )

            # Keep the last block as lightweight overlap.
            overlap_blocks = []

            overlap_length = 0

            for previous_block in reversed(current_blocks):
                if overlap_length + len(previous_block) > chunk_overlap:
                    break

                overlap_blocks.insert(0, previous_block)
                overlap_length += len(previous_block) + 2

            current_blocks = overlap_blocks
            current_length = overlap_length

        current_blocks.append(block)
        current_length += block_length + 2

    if current_blocks:
        chunks.append(
            "\n\n".join(current_blocks).strip()
        )

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Create structure-aware chunks from extracted PDF text.
    """

    blocks = split_into_blocks(text)

    return combine_blocks(
        blocks=blocks,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def create_evidence_chunks(
    evidence_pages: list[dict[str, Any]],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """
    Create evidence chunks while preserving source metadata.

    Each chunk receives a globally unique chunk_id.
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
                    "chunk_id": (
                        f"{page_data.get('file_name', 'document')}"
                        f"_p{page_data.get('page')}"
                        f"_c{chunk_index}"
                    ),
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