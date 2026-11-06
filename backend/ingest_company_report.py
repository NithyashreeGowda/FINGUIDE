from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from company_master import Nifty500CompanyMaster
from rag.chunker import create_evidence_chunks
from rag.document_loader import load_financial_document
from rag.embeddings import EmbeddingModel
from rag.source_registry import FinancialSourceRegistry
from rag.vector_store import VectorStore


BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
DEFAULT_INDEX_PATH = DATA_DIR / "faiss_index.index"
DEFAULT_METADATA_PATH = DATA_DIR / "faiss_metadata.json"
DOCUMENT_MANIFEST_PATH = (
    DATA_DIR / "company_discovery" / "financial_document_manifest.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not write {path}: {exc}") from exc


def _validate_report_content(
    text: str,
    company_name: str,
    financial_year: str,
    scope: str,
) -> None:
    normalized_text = text.casefold()
    company_tokens = [
        token.casefold()
        for token in company_name.replace(".", "").split()
        if token.casefold() not in {"limited", "ltd", "inc", "plc"}
    ]
    identity = " ".join(company_tokens[:2])
    if not identity or identity not in normalized_text:
        raise ValueError(
            f"Extracted report text does not identify company {company_name!r}."
        )

    year_token = financial_year.strip().upper().removeprefix("FY").strip()
    if year_token not in text.upper().replace(" ", ""):
        if year_token.replace("-", "/") not in text.upper().replace(" ", ""):
            raise ValueError(
                f"Extracted report text does not contain financial year {financial_year!r}."
            )

    if scope == "standalone_and_consolidated":
        if "standalone" not in normalized_text or "consolidated" not in normalized_text:
            raise ValueError(
                "The report does not contain both standalone and consolidated sections."
            )
    elif scope in {"standalone", "consolidated"} and scope not in normalized_text:
        raise ValueError(f"The report does not contain the declared {scope} scope.")


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "documents": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read document manifest {path}: {exc}") from exc
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or not isinstance(data.get("documents"), list)
    ):
        raise ValueError(f"Document manifest has an invalid schema: {path}")
    return data


def ingest_company_report(
    *,
    file_path: str | Path,
    symbol: str,
    financial_year: str,
    source_url: str,
    source_label: str,
    source_organization: str,
    reporting_period: str,
    scope: str,
    document_type: str = "annual_report",
    publication_date: str | None = None,
    expected_sha256: str | None = None,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
    manifest_path: str | Path = DOCUMENT_MANIFEST_PATH,
) -> dict[str, Any]:
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Financial report not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Only validated PDF annual reports are supported.")
    if not financial_year.strip() or not reporting_period.strip():
        raise ValueError("financial_year and reporting_period are required.")
    if scope not in {
        "standalone",
        "consolidated",
        "standalone_and_consolidated",
        "unspecified",
    }:
        raise ValueError("Unsupported reporting scope.")
    if publication_date is not None:
        try:
            datetime.strptime(publication_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("publication_date must be an ISO date (YYYY-MM-DD).") from exc

    master = Nifty500CompanyMaster()
    company = master.get_company_by_symbol(symbol)
    if company is None:
        raise ValueError(f"Symbol is not present in the verified company master: {symbol}")
    normalized_symbol = company["symbol"]
    company_id = company["company_id"]

    registry = FinancialSourceRegistry()
    registered_source = registry.get_source_by_url(
        company_id=company_id,
        url=source_url,
    )
    if (
        registered_source is None
        or registered_source.get("verification_status") != "verified"
    ):
        raise ValueError(
            "The source URL must already be registered as verified for this company."
        )

    document_hash = _sha256(path)
    if expected_sha256 and document_hash.casefold() != expected_sha256.strip().casefold():
        raise ValueError(
            f"PDF SHA-256 does not match the verified source: {document_hash}"
        )

    date_match = reporting_period.rsplit("/", 1)[-1]
    document = load_financial_document(
        str(path),
        source=source_label,
        company=company["name"],
        document_type=document_type,
        document_date=date_match,
        source_url=source_url,
        symbol=normalized_symbol,
        financial_year=financial_year,
        reporting_period=reporting_period,
        scope=scope,
        publication_date=publication_date,
        source_organization=source_organization,
        verification_status="verified",
    )
    extracted_text = "\n".join(
        page["text"] for page in document["evidence"]
    )
    if not extracted_text.strip():
        raise ValueError("The PDF produced no extractable text.")
    _validate_report_content(
        extracted_text,
        company["name"],
        financial_year,
        scope,
    )

    chunks = create_evidence_chunks(document["evidence"])
    if not chunks:
        raise ValueError("No evidence chunks were created from the PDF.")
    if len({chunk["chunk_id"] for chunk in chunks}) != len(chunks):
        raise ValueError("The PDF generated duplicate chunk identifiers.")

    index_path = Path(index_path).resolve()
    metadata_path = Path(metadata_path).resolve()
    manifest_path = Path(manifest_path).resolve()
    if not index_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError(
            "An existing active FAISS index and metadata file are required for safe append."
        )

    vector_store = VectorStore(dimension=384)
    vector_store.load(str(index_path), str(metadata_path))

    if any(
        record.get("document_id") == document["document_id"]
        or record.get("source_sha256") == document_hash
        for record in vector_store.metadata
    ):
        return {
            "status": "already_ingested",
            "symbol": normalized_symbol,
            "financial_year": financial_year,
            "document_id": document["document_id"],
            "sha256": document_hash,
            "chunks_added": 0,
            "vector_count": vector_store.index.ntotal,
        }

    existing_chunk_ids = {
        record.get("chunk_id")
        for record in vector_store.metadata
        if record.get("chunk_id")
    }
    chunks = [
        chunk for chunk in chunks
        if chunk["chunk_id"] not in existing_chunk_ids
    ]
    if not chunks:
        raise ValueError(
            "All generated chunks already exist in the index, but no matching document ID was found."
        )

    embedding_model = EmbeddingModel()
    embeddings = embedding_model.encode_texts(
        [chunk["text"] for chunk in chunks]
    )
    if len(embeddings) != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    vector_store.add_embeddings(embeddings, chunks)
    if vector_store.index.ntotal != len(vector_store.metadata):
        raise ValueError("FAISS vectors and metadata are misaligned.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="finguide-index-stage-",
        dir=str(index_path.parent),
    ) as stage_dir:
        staged_index = Path(stage_dir) / "faiss_index.index"
        staged_metadata = Path(stage_dir) / "faiss_metadata.json"
        vector_store.save(str(staged_index), str(staged_metadata))

        validation_store = VectorStore(dimension=384)
        validation_store.load(str(staged_index), str(staged_metadata))
        if validation_store.index.ntotal != len(validation_store.metadata):
            raise ValueError("Staged FAISS index failed integrity validation.")
        if not any(
            item.get("document_id") == document["document_id"]
            and item.get("symbol") == normalized_symbol
            and item.get("financial_year") == financial_year
            for item in validation_store.metadata
        ):
            raise ValueError("Staged index is missing the new report metadata.")

        backup_dir = (
            index_path.parent
            / "faiss_backups"
            / f"before-{stamp}"
        )
        backup_dir.mkdir(parents=True, exist_ok=False)
        backup_index = backup_dir / index_path.name
        backup_metadata = backup_dir / metadata_path.name
        shutil.copy2(index_path, backup_index)
        shutil.copy2(metadata_path, backup_metadata)

        index_replaced = False
        try:
            os.replace(staged_index, index_path)
            index_replaced = True
            os.replace(staged_metadata, metadata_path)
        except OSError as exc:
            if index_replaced:
                shutil.copy2(backup_index, index_path)
            shutil.copy2(backup_metadata, metadata_path)
            raise RuntimeError(
                f"Could not safely activate the staged index; previous files restored: {exc}"
            ) from exc

    manifest = _read_manifest(manifest_path)
    manifest["documents"] = [
        entry
        for entry in manifest["documents"]
        if entry.get("sha256") != document_hash
    ]
    manifest["documents"].append({
        "symbol": normalized_symbol,
        "company": company["name"],
        "financial_year": financial_year,
        "document_type": document_type,
        "format": "pdf",
        "scope": scope,
        "reporting_period": reporting_period,
        "source_url": source_url,
        "source_organization": source_organization,
        "local_path": str(path.relative_to(BACKEND_DIR)),
        "publication_date": publication_date,
        "sha256": document_hash,
        "document_id": document["document_id"],
        "download_status": "verified",
        "extraction_status": "success",
        "ingestion_status": "success",
        "page_count": document["page_count"],
        "evidence_chunk_count": len(chunks),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    })
    _write_json_atomic(manifest_path, manifest)

    return {
        "status": "ingested",
        "symbol": normalized_symbol,
        "company": company["name"],
        "financial_year": financial_year,
        "document_id": document["document_id"],
        "sha256": document_hash,
        "page_count": document["page_count"],
        "chunks_added": len(chunks),
        "vector_count": vector_store.index.ntotal,
        "index_path": str(index_path),
        "metadata_path": str(metadata_path),
        "backup_directory": str(backup_dir),
        "manifest_path": str(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and append an official company annual report to the active FAISS index."
    )
    parser.add_argument("--file", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--financial-year", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--source-organization", required=True)
    parser.add_argument("--reporting-period", required=True)
    parser.add_argument(
        "--scope",
        choices=(
            "standalone",
            "consolidated",
            "standalone_and_consolidated",
            "unspecified",
        ),
        required=True,
    )
    parser.add_argument("--document-type", default="annual_report")
    parser.add_argument("--publication-date")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()

    result = ingest_company_report(
        file_path=args.file,
        symbol=args.symbol,
        financial_year=args.financial_year,
        source_url=args.source_url,
        source_label=args.source_label,
        source_organization=args.source_organization,
        reporting_period=args.reporting_period,
        scope=args.scope,
        document_type=args.document_type,
        publication_date=args.publication_date,
        expected_sha256=args.expected_sha256,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
