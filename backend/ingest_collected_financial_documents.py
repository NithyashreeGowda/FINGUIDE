from __future__ import annotations

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
DOCUMENT_DIR = DATA_DIR / "financial_documents"
INDEX_PATH = DATA_DIR / "faiss_index.index"
METADATA_PATH = DATA_DIR / "faiss_metadata.json"
MANIFEST_PATH = (
    DATA_DIR / "company_discovery" / "financial_document_manifest.json"
)

# These are distinct company financial reports already present in the workspace.
# Exact byte-for-byte copies are skipped by SHA-256 during ingestion.
COLLECTED_DOCUMENTS = (
    {
        "path": "Annual-Report-2024-25_0.pdf",
        "symbol": "HCLTECH",
        "financial_year": "FY2024-25",
        "document_type": "annual_report",
        "period_start": "2024-04-01",
        "period_end": "2025-03-31",
        "scope": "standalone_and_consolidated",
        "aliases": ("HCLTech", "HCL Technologies"),
    },
    {
        "path": "HCLTech-Annual-Report-FY-2025-26.pdf",
        "symbol": "HCLTECH",
        "financial_year": "FY2025-26",
        "document_type": "annual_report",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "scope": "standalone_and_consolidated",
        "aliases": ("HCLTech", "HCL Technologies"),
    },
    {
        "path": "AnnualReturn2026.pdf",
        "symbol": "HCLTECH",
        "financial_year": "FY2025-26",
        "document_type": "annual_return",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "aliases": ("HCL Technologies", "HCL TECHNOLOGIES LIMITED"),
        "year_markers": ("31/03/2026",),
    },
    {
        "path": "HDFC_Bank_IR26.pdf",
        "symbol": "HDFCBANK",
        "financial_year": "FY2025-26",
        "document_type": "annual_report",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "scope": "standalone_and_consolidated",
        "aliases": ("HDFC Bank",),
    },
    {
        "path": "ICICI-Bank-AR2025-2026_narrative.pdf",
        "symbol": "ICICIBANK",
        "financial_year": "FY2025-26",
        "document_type": "annual_report",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "scope": "unspecified",
        "aliases": ("ICICI Bank",),
    },
    {
        "path": "icici-bank-ar-2026-boards-report.pdf",
        "symbol": "ICICIBANK",
        "financial_year": "FY2025-26",
        "document_type": "board_report",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "scope": "unspecified",
        "aliases": ("ICICI Bank",),
    },
    {
        "path": "q1-2027.pdf",
        "symbol": "INFY",
        "financial_year": "FY2026-27",
        "document_type": "quarterly_ratio_analysis",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "scope": "unspecified",
        "aliases": ("Infosys Limited",),
        "year_markers": ("June 30, 2026",),
    },
    {
        "path": "consolidated-financial-statement-q2fy27.pdf",
        "symbol": "WIPRO",
        "financial_year": "FY2026-27",
        "document_type": "quarterly_financial_statement",
        "period_start": "2026-04-01",
        "period_end": "2026-09-30",
        "scope": "consolidated",
        "aliases": ("Wipro Limited",),
        "year_markers": ("September 30, 2026",),
    },
    {
        "path": "datasheet-q2fy27.pdf",
        "symbol": "WIPRO",
        "financial_year": "FY2026-27",
        "document_type": "quarterly_datasheet",
        "period_start": "2026-07-01",
        "period_end": "2026-09-30",
        "aliases": ("Wipro",),
        "year_markers": ("September 30, 2026",),
    },
    {
        "path": "regulation-33-financial-results-q2fy27.pdf",
        "symbol": "WIPRO",
        "financial_year": "FY2026-27",
        "document_type": "quarterly_financial_results",
        "period_start": "2026-04-01",
        "period_end": "2026-09-30",
        "scope": "standalone_and_consolidated",
        "aliases": ("Wipro Limited",),
        "year_markers": ("September 30, 2026",),
    },
    {
        "path": "wipro-investor-ppt-q2fy27.pdf",
        "symbol": "WIPRO",
        "financial_year": "FY2026-27",
        "document_type": "investor_presentation",
        "period_start": "2026-07-01",
        "period_end": "2026-09-30",
        "aliases": ("Wipro Limited",),
        "year_markers": ("September 30, 2026", "September 30, 2026"),
    },
    {
        "path": "incoming/RELIANCE_2023_2024.pdf",
        "symbol": "RELIANCE",
        "financial_year": "FY2023-24",
        "document_type": "annual_report",
        "period_start": "2023-04-01",
        "period_end": "2024-03-31",
        "scope": "standalone_and_consolidated",
        "aliases": ("Reliance Industries",),
    },
    {
        "path": "incoming/Reliance-2024-25.pdf",
        "symbol": "RELIANCE",
        "financial_year": "FY2024-25",
        "document_type": "annual_report_alternate_copy",
        "period_start": "2024-04-01",
        "period_end": "2025-03-31",
        "scope": "standalone_and_consolidated",
        "aliases": ("Reliance Industries",),
    },
    {
        "path": "incoming/RELIANCE_2025_2026.pdf",
        "symbol": "RELIANCE",
        "financial_year": "FY2025-26",
        "document_type": "annual_report",
        "period_start": "2025-04-01",
        "period_end": "2026-03-31",
        "scope": "standalone_and_consolidated",
        "aliases": ("Reliance Industries",),
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"schema_version": 1, "documents": []}
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read manifest {MANIFEST_PATH}: {exc}") from exc
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or not isinstance(data.get("documents"), list)
    ):
        raise ValueError(f"Invalid document manifest schema: {MANIFEST_PATH}")
    return data


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    except (OSError, RuntimeError) as exc:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not write {path}: {exc}") from exc


def _financial_year_markers(financial_year: str) -> tuple[str, ...]:
    years = financial_year.removeprefix("FY")
    start, end = years.split("-", 1)
    full_end = str(int(start[:2] + end))
    return (
        years,
        years.replace("-", "-"),
        f"{start}-{full_end}",
        f"FY {years}",
    )


def _scope_for(text: str, declared_scope: str | None) -> str:
    if declared_scope:
        return declared_scope
    normalized = text.casefold()
    if "standalone" in normalized and "consolidated" in normalized:
        return "standalone_and_consolidated"
    if "consolidated" in normalized:
        return "consolidated"
    if "standalone" in normalized:
        return "standalone"
    return "unspecified"


def _prepare_document(
    entry: dict[str, Any],
    companies_by_symbol: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = (DOCUMENT_DIR / entry["path"]).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Collected document does not exist: {path}")

    company = companies_by_symbol.get(entry["symbol"])
    if company is None:
        raise ValueError(
            f"Symbol is absent from the source-backed company master: {entry['symbol']}"
        )

    document_hash = _sha256(path)
    source_label = (
        f"{company['name']} {entry['document_type']} "
        f"{entry['financial_year']} (local file: {path.name})"
    )
    document = load_financial_document(
        str(path),
        source=source_label,
        company=company["name"],
        document_type=entry["document_type"],
        document_date=entry["period_end"],
        symbol=entry["symbol"],
        financial_year=entry["financial_year"],
        reporting_period=f"{entry['period_start']}/{entry['period_end']}",
        scope="unspecified",
        source_organization=company["name"],
        verification_status="unverified",
    )
    extracted_text = "\n".join(
        page["text"] for page in document["evidence"]
    )
    normalized_text = extracted_text.casefold()
    if not extracted_text.strip():
        raise ValueError(f"No extractable text in {path.name}.")
    if not any(alias.casefold() in normalized_text for alias in entry["aliases"]):
        raise ValueError(
            f"Extracted text in {path.name} does not identify {company['name']}."
        )

    year_markers = entry.get(
        "year_markers",
        _financial_year_markers(entry["financial_year"]),
    )
    if not any(marker.casefold() in normalized_text for marker in year_markers):
        raise ValueError(
            f"Extracted text in {path.name} does not contain its declared period "
            f"{entry['financial_year']}."
        )

    scope = _scope_for(extracted_text, entry.get("scope"))
    for evidence in document["evidence"]:
        evidence["scope"] = scope
        evidence["source_sha256"] = document_hash

    chunks = create_evidence_chunks(document["evidence"])
    if not chunks:
        raise ValueError(f"No evidence chunks were created from {path.name}.")
    if len({chunk["chunk_id"] for chunk in chunks}) != len(chunks):
        raise ValueError(f"Duplicate chunk identifiers in {path.name}.")

    manifest_entry = {
        "symbol": entry["symbol"],
        "company": company["name"],
        "financial_year": entry["financial_year"],
        "document_type": entry["document_type"],
        "format": "pdf",
        "scope": scope,
        "reporting_period": f"{entry['period_start']}/{entry['period_end']}",
        "source_url": None,
        "source_organization": company["name"],
        "source_verification_status": "unverified",
        "source_verification_note": (
            "Local report content and company/year were checked. "
            "The original official URL was not available for verification."
        ),
        "local_path": str(path.relative_to(BACKEND_DIR)),
        "publication_date": None,
        "sha256": document_hash,
        "document_id": document["document_id"],
        "download_status": "local_file_present",
        "extraction_status": "success",
        "ingestion_status": "success",
        "page_count": document["page_count"],
        "evidence_chunk_count": len(chunks),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    return manifest_entry, chunks


def ingest_collected_documents() -> dict[str, Any]:
    master = Nifty500CompanyMaster()
    companies = master.list_companies()
    companies_by_symbol = {
        company["symbol"]: company
        for company in companies
    }
    registry = FinancialSourceRegistry()

    prepared: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    seen_hashes: set[str] = set()
    for entry in COLLECTED_DOCUMENTS:
        manifest_entry, chunks = _prepare_document(entry, companies_by_symbol)
        digest = manifest_entry["sha256"]
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        prepared.append((manifest_entry, chunks))

    index_path = INDEX_PATH.resolve()
    metadata_path = METADATA_PATH.resolve()
    if not index_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError("The active FAISS index and metadata are required.")

    store = VectorStore(dimension=384)
    store.load(str(index_path), str(metadata_path))
    if store.index.ntotal != len(store.metadata):
        raise ValueError("Active FAISS vectors and metadata are misaligned.")

    existing_hashes = {
        record.get("source_sha256") or record.get("document_id")
        for record in store.metadata
    }
    new_documents = [
        (manifest_entry, chunks)
        for manifest_entry, chunks in prepared
        if manifest_entry["sha256"] not in existing_hashes
    ]

    manifest = _read_manifest()
    if not new_documents:
        return {
            "status": "already_ingested",
            "vector_count": store.index.ntotal,
            "documents_added": 0,
            "manifest_path": str(MANIFEST_PATH),
        }

    for symbol in sorted({item["symbol"] for item, _ in new_documents}):
        company = companies_by_symbol[symbol]
        registry.upsert_company(
            company_id=company["company_id"],
            name=company["name"],
            country=company["country"],
            symbol=symbol,
            exchange=company.get("exchange"),
        )

    chunks_to_add = [
        chunk
        for _, chunks in new_documents
        for chunk in chunks
    ]
    embedding_model = EmbeddingModel()
    embeddings = embedding_model.encode_texts(
        [chunk["text"] for chunk in chunks_to_add]
    )
    if len(embeddings) != len(chunks_to_add):
        raise ValueError("Embedding count does not match the collected chunks.")

    store.add_embeddings(embeddings, chunks_to_add)
    if store.index.ntotal != len(store.metadata):
        raise ValueError("Updated FAISS vectors and metadata are misaligned.")

    updated_manifest = dict(manifest)
    new_hashes = {item["sha256"] for item, _ in new_documents}
    updated_manifest["documents"] = [
        item
        for item in manifest["documents"]
        if item.get("sha256") not in new_hashes
    ] + [item for item, _ in new_documents]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = DATA_DIR / "faiss_backups" / f"before-local-batch-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory(
        prefix="finguide-local-batch-",
        dir=str(DATA_DIR),
    ) as stage_dir:
        staged_index = Path(stage_dir) / index_path.name
        staged_metadata = Path(stage_dir) / metadata_path.name
        store.save(str(staged_index), str(staged_metadata))

        validation_store = VectorStore(dimension=384)
        validation_store.load(str(staged_index), str(staged_metadata))
        if validation_store.index.ntotal != len(validation_store.metadata):
            raise ValueError("Staged FAISS index failed integrity validation.")
        expected_new_ids = {
            item["document_id"] for item, _ in new_documents
        }
        actual_new_ids = {
            record.get("document_id")
            for record in validation_store.metadata
            if record.get("document_id") in expected_new_ids
        }
        if actual_new_ids != expected_new_ids:
            raise ValueError("Staged index is missing one or more new reports.")

        backup_index = backup_dir / index_path.name
        backup_metadata = backup_dir / metadata_path.name
        shutil.copy2(index_path, backup_index)
        shutil.copy2(metadata_path, backup_metadata)
        backup_manifest = None
        if MANIFEST_PATH.exists():
            backup_manifest = backup_dir / MANIFEST_PATH.name
            shutil.copy2(MANIFEST_PATH, backup_manifest)

        index_replaced = False
        try:
            os.replace(staged_index, index_path)
            index_replaced = True
            os.replace(staged_metadata, metadata_path)
            _write_json_atomic(MANIFEST_PATH, updated_manifest)
        except (OSError, RuntimeError) as exc:
            if index_replaced:
                shutil.copy2(backup_index, index_path)
            shutil.copy2(backup_metadata, metadata_path)
            if backup_manifest is not None:
                shutil.copy2(backup_manifest, MANIFEST_PATH)
            raise RuntimeError(
                f"Could not safely activate the batch; previous index restored: {exc}"
            ) from exc

    return {
        "status": "ingested",
        "documents_added": len(new_documents),
        "vectors_added": len(chunks_to_add),
        "vector_count": store.index.ntotal,
        "documents": [
            {
                "symbol": item["symbol"],
                "financial_year": item["financial_year"],
                "document_type": item["document_type"],
                "local_path": item["local_path"],
                "page_count": item["page_count"],
                "chunks": item["evidence_chunk_count"],
                "verification_status": item["source_verification_status"],
            }
            for item, _ in new_documents
        ],
        "backup_directory": str(backup_dir),
        "manifest_path": str(MANIFEST_PATH),
    }


if __name__ == "__main__":
    print(json.dumps(ingest_collected_documents(), ensure_ascii=False, indent=2))
