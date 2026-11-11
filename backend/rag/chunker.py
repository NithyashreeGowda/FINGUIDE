from __future__ import annotations

import hashlib
import re
from typing import Any


def clean_text(text: str) -> str:
    """Normalize extracted content without company-specific cleanup rules."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\n[ \t]+\n", "\n\n", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def split_into_blocks(text: str) -> list[str]:
    """Split text into logical blocks using blank lines."""
    text = clean_text(text)
    if not text:
        return []

    blocks = []
    for raw_block in re.split(r"\n\s*\n", text):
        block = raw_block.strip()
        if block:
            blocks.append(block)
    return blocks


def combine_blocks(
    blocks: list[str],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    """Combine blocks into chunks while preserving boundaries and overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")
    if not blocks:
        return []

    chunks: list[str] = []
    current_blocks: list[str] = []
    current_length = 0

    for block in blocks:
        block_length = len(block)
        if current_blocks and current_length + block_length + 2 > chunk_size:
            chunks.append("\n\n".join(current_blocks).strip())

            overlap_blocks: list[str] = []
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
        chunks.append("\n\n".join(current_blocks).strip())

    filtered = [chunk for chunk in chunks if chunk.strip()]
    return filtered


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    """Create structure-aware chunks from extracted text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string.")
    blocks = split_into_blocks(text)
    return combine_blocks(
        blocks=blocks,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def _stable_chunk_id(page_data: dict[str, Any], chunk_index: int, chunk: str) -> str:
    seed = f"{page_data.get('document_id') or page_data.get('file_name') or 'document'}|{page_data.get('page')}|{chunk_index}|{chunk[:200]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def create_evidence_chunks(
    evidence_pages: list[dict[str, Any]],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """Create evidence chunks while preserving source metadata and avoiding duplicates."""
    if evidence_pages is None:
        return []

    all_chunks: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    preserved_metadata = (
        "symbol",
        "financial_year",
        "reporting_period",
        "scope",
        "publication_date",
        "source_organization",
        "verification_status",
        "source_sha256",
    )

    for page_data in evidence_pages:
        if not isinstance(page_data, dict):
            continue

        text = page_data.get("text", "") or ""
        if not isinstance(text, str):
            text = str(text)

        chunks = chunk_text(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk_index, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            chunk_id = _stable_chunk_id(page_data, chunk_index, chunk)
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)

            evidence_chunk = {
                "chunk_id": chunk_id,
                "text": chunk,
                "source": page_data.get("source"),
                "date": page_data.get("date"),
                "company": page_data.get("company"),
                "document_type": page_data.get("document_type"),
                "page": page_data.get("page"),
                "file_name": page_data.get("file_name"),
                "chunk_index": chunk_index,
                "source_url": page_data.get("source_url"),
                "document_id": page_data.get("document_id"),
                "ingestion_timestamp": page_data.get("ingestion_timestamp"),
            }
            evidence_chunk.update({
                key: page_data[key]
                for key in preserved_metadata
                if key in page_data
            })
            all_chunks.append(evidence_chunk)

    return all_chunks
    