import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.retreiver import FinancialRetriever
from rag.evidence_validator import EvidenceValidator


vector_store = VectorStore(dimension=384)

vector_store.load(
    index_path=str(BACKEND_DIR / "data" / "faiss_index.index"),
    metadata_path=str(BACKEND_DIR / "data" / "faiss_metadata.json"),
)

embedding_model = EmbeddingModel()

retriever = FinancialRetriever(
    vector_store=vector_store,
    embedding_model=embedding_model,
)

validator = EvidenceValidator(
    freshness_days=365
)

query = "What was Reliance's financial performance?"

results = retriever.retrieve(
    query=query,
    top_k=5
)

print("QUERY:")
print(query)

print()
print("=" * 70)
print("EVIDENCE VALIDATION")
print("=" * 70)

for index, result in enumerate(results, start=1):

    validation = validator.validate_evidence(
        evidence=result,
        minimum_similarity=0.50,
    )

    print()
    print("-" * 70)
    print(f"RESULT {index}")
    print("-" * 70)

    print("Company:", result.get("company"))
    print("Source:", result.get("source"))
    print("Date:", result.get("date"))
    print("Page:", result.get("page"))
    print("Similarity:", result.get("score"))

    print()
    print("Metadata valid:")
    print(validation["metadata"]["valid"])

    print("Age in days:")
    print(validation["freshness"]["age_days"])

    print("Fresh:")
    print(validation["freshness"]["is_fresh"])

    print("Relevant:")
    print(validation["relevance"]["is_relevant"])

    print("Evidence valid:")
    print(validation["valid"])

    if validation["validation_errors"]:
        print("Validation errors:")
        for error in validation["validation_errors"]:
            print("-", error)