import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.chunker import create_evidence_chunks
from rag.vector_store import VectorStore


def test_chunker_preserves_filter_and_citation_metadata():
    chunks = create_evidence_chunks([{
        "text": "Revenue from operations was reported.",
        "source": "Official annual report",
        "source_url": "https://example.com/report.pdf",
        "company": "Tata Consultancy Services Ltd.",
        "symbol": "TCS",
        "financial_year": "FY2025-26",
        "reporting_period": "2025-04-01/2026-03-31",
        "scope": "standalone_and_consolidated",
        "publication_date": None,
        "source_organization": "Tata Consultancy Services",
        "verification_status": "verified",
        "document_type": "annual_report",
        "page": 7,
        "document_id": "sha256:abc",
    }])

    assert len(chunks) == 1
    assert chunks[0]["symbol"] == "TCS"
    assert chunks[0]["financial_year"] == "FY2025-26"
    assert chunks[0]["page"] == 7
    assert chunks[0]["source_url"] == "https://example.com/report.pdf"
    assert chunks[0]["verification_status"] == "verified"


def test_vector_search_applies_combined_company_symbol_and_year_filters():
    store = VectorStore(dimension=3)
    store.add_embeddings(
        [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.8, 0.2, 0.0],
        ],
        [
            {
                "company": "Reliance Industries Ltd.",
                "symbol": "RELIANCE",
                "financial_year": "FY2024-25",
                "text": "reliance",
            },
            {
                "company": "Tata Consultancy Services Ltd.",
                "symbol": "TCS",
                "financial_year": "FY2025-26",
                "text": "tcs latest",
            },
            {
                "company": "Tata Consultancy Services Ltd.",
                "symbol": "TCS",
                "financial_year": "FY2024-25",
                "text": "tcs previous",
            },
        ],
    )

    results = store.search(
        [1.0, 0.0, 0.0],
        top_k=1,
        metadata_filters={
            "symbol": "tcs",
            "financial_year": "2025-26",
        },
    )

    assert len(results) == 1
    assert results[0]["symbol"] == "TCS"
    assert results[0]["financial_year"] == "FY2025-26"


def test_vector_search_rejects_unknown_filter_fields():
    store = VectorStore(dimension=2)
    store.add_embeddings([[1.0, 0.0]], [{"symbol": "TCS"}])

    with pytest.raises(ValueError, match="Unsupported metadata filters"):
        store.search([1.0, 0.0], metadata_filters={"financial_yeer": "FY2025-26"})
