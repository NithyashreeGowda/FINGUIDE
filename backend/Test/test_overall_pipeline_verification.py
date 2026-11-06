import json
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.chunker import create_evidence_chunks
from rag.document_loader import load_financial_document
from rag.embeddings import EmbeddingModel
from rag.retreiver import FinancialRetriever
from rag.vector_store import VectorStore

REAL_DOC_PATH = (
    BACKEND_DIR
    / "data"
    / "financial_documents"
    / "incoming"
    / "RELIANCE_2024_2025.pdf"
)
REAL_INDEX_PATH = BACKEND_DIR / "data" / "faiss_index.index"
REAL_METADATA_PATH = BACKEND_DIR / "data" / "faiss_metadata.json"


def test_reliance_document_metadata_and_text_are_preserved():
    document = load_financial_document(
        str(REAL_DOC_PATH),
        source="Reliance Industries Limited Annual Report 2024-25",
        company="Reliance Industries Limited",
        document_type="annual_report",
        document_date="2025-03-31",
    )

    assert document["company"] == "Reliance Industries Limited"
    assert document["document_type"] == "annual_report"
    assert document["date"] == "2025-03-31"
    assert document["page_count"] > 1
    assert all(entry["text"].strip() for entry in document["evidence"])
    assert all(entry["source"] == "Reliance Industries Limited Annual Report 2024-25" for entry in document["evidence"])


def test_chunker_preserves_metadata_and_prevents_duplicate_chunks():
    evidence_pages = [
        {
            "document_id": "doc-1",
            "file_name": "demo.pdf",
            "source": "Demo source",
            "source_url": "https://example.com/report",
            "date": "2025-03-31",
            "company": "Reliance Industries Limited",
            "document_type": "annual_report",
            "page": 1,
            "text": "Revenue from operations\n\nProfit after tax\n\n" + ("A " * 120),
        },
        {
            "document_id": "doc-1",
            "file_name": "demo.pdf",
            "source": "Demo source",
            "source_url": "https://example.com/report",
            "date": "2025-03-31",
            "company": "Reliance Industries Limited",
            "document_type": "annual_report",
            "page": 2,
            "text": "Revenue from operations\n\nProfit after tax\n\n" + ("A " * 120),
        },
    ]

    chunks = create_evidence_chunks(evidence_pages, chunk_size=200, chunk_overlap=40)

    assert chunks
    assert len({chunk["chunk_id"] for chunk in chunks}) == len(chunks)
    assert all(chunk["company"] == "Reliance Industries Limited" for chunk in chunks)
    assert {chunk["page"] for chunk in chunks}.issubset({1, 2})
    assert all(chunk["document_type"] == "annual_report" for chunk in chunks)


def test_embedding_model_has_expected_dimension_and_protects_invalid_input():
    model = EmbeddingModel()
    embeddings = model.encode_texts([
        "Revenue from operations for FY2025 was strong.",
        "Profit after tax improved materially year on year.",
    ])

    assert len(embeddings) == 2
    assert all(len(vector) == 384 for vector in embeddings)
    assert all(np.isfinite(np.asarray(vector, dtype=np.float32)).all() for vector in embeddings)

    with pytest.raises(ValueError):
        model.encode_texts([""])


def test_vector_store_save_and_load_round_trip(tmp_path):
    model = EmbeddingModel()
    embeddings = model.encode_texts([
        "Revenue from operations grew in FY2025.",
        "Finance cost declined and leverage improved.",
    ])

    metadata = [
        {"chunk_id": "c1", "company": "Reliance Industries Limited", "page": 1, "text": "Revenue..."},
        {"chunk_id": "c2", "company": "Reliance Industries Limited", "page": 2, "text": "Finance..."},
    ]

    store = VectorStore(dimension=384)
    store.add_embeddings(embeddings, metadata)

    index_path = tmp_path / "tmp_index.index"
    metadata_path = tmp_path / "tmp_metadata.json"
    store.save(str(index_path), str(metadata_path))

    restored = VectorStore(dimension=384)
    restored.load(str(index_path), str(metadata_path))

    assert restored.index.ntotal == 2
    assert len(restored.metadata) == 2
    assert restored.metadata[0]["chunk_id"] == "c1"
    assert restored.metadata[1]["chunk_id"] == "c2"


def test_actual_retriever_returns_company_evidence_from_project_index():
    vector_store = VectorStore(dimension=384)
    vector_store.load(
        index_path=str(REAL_INDEX_PATH),
        metadata_path=str(REAL_METADATA_PATH),
    )

    retriever = FinancialRetriever(
        vector_store=vector_store,
        embedding_model=EmbeddingModel(),
    )

    results = retriever.retrieve(
        query="What was Reliance's revenue in FY2025?",
        top_k=5,
        minimum_score=0.50,
        symbol="RELIANCE",
        financial_year="FY2024-25",
    )

    assert results
    assert all(result.get("company") == "Reliance Industries Ltd." for result in results)
    assert all(result.get("symbol") == "RELIANCE" for result in results)
    assert all(result.get("financial_year") == "FY2024-25" for result in results)
    assert all(isinstance(result.get("page"), int) for result in results)
    assert all(isinstance(result.get("text"), str) and result["text"].strip() for result in results)


def test_project_index_contains_all_ingested_company_reports():
    financial_documents = BACKEND_DIR / "data" / "financial_documents"
    assert (
        financial_documents / "incoming" / "RELIANCE_2024_2025.pdf"
    ).is_file()
    assert (financial_documents / "TCS_Annual_Report_2025-26.pdf").is_file()
    assert (financial_documents / "infosys-ar-26.pdf").is_file()

    with open(REAL_METADATA_PATH, "r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    symbols = {item.get("symbol") for item in metadata if item.get("symbol")}
    assert symbols >= {"RELIANCE", "TCS", "INFY"}
    store = VectorStore(dimension=384)
    store.load(str(REAL_INDEX_PATH), str(REAL_METADATA_PATH))
    assert store.index.ntotal == len(metadata)
