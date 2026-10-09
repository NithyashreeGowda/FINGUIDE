
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .embeddings import EmbeddingModel
from .vector_store import VectorStore
from .reranker import EvidenceReranker
from .retreiver import FinancialRetriever
from .evidence_validator import validate_evidence


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=3)
    claim: str | None = None
    metric: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)

    # Configurable evidence freshness policy.
    freshness_period_months: int = Field(
        default=12,
        ge=1,
        le=120,
    )


class RAGResponse(BaseModel):
    query: str
    evidence: list[dict[str, Any]]
    validation: dict[str, Any]


def _json_safe(value):
    """Convert dates and nested values into JSON-compatible values."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


# Load RAG components once when the API module starts.
embedding_model = EmbeddingModel()

vector_store = VectorStore(
    dimension=384,
)

vector_store.load(
    index_path="data/faiss_index.index",
    metadata_path="data/faiss_metadata.json",
)

reranker = EvidenceReranker()

retriever = FinancialRetriever(
    vector_store=vector_store,
    embedding_model=embedding_model,
    reranker=reranker,
)


@router.post("/query", response_model=RAGResponse)
def rag_query(request: RAGRequest):
    try:
        # Retrieve relevant financial evidence.
        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
        )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant financial evidence found.",
            )

        evidence = []

        for result in results:
            item = dict(result)

            # Preserve the existing metadata fallback behavior.
            if "date" not in item:
                item["date"] = date.today()

            if "document_type" not in item:
                item["document_type"] = (
                    "official_company_report"
                )

            evidence.append(
                _json_safe(item)
            )

        # Validate source quality, freshness, claim support,
        # and conflicting evidence.
        validation = validate_evidence(
            evidence_results=evidence,
            claim=request.claim,
            metric=request.metric,
            freshness_period_months=(
                request.freshness_period_months
            ),
        )

        return {
            "query": request.query,
            "evidence": evidence,
            "validation": _json_safe(validation),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {str(exc)}",
        )