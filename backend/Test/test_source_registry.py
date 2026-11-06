import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.source_registry import FinancialSourceRegistry


def test_registry_lookup_and_filters(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry = FinancialSourceRegistry(registry_path)

    registry.register_company(
        company_id="reliance",
        name="Reliance Industries",
        country="India",
        symbol="reliance",
        exchange="NSE",
        filing_source_urls=["https://example.com/reliance/annual-report"],
        document_categories=["annual_report"],
    )

    registry.register_source(
        company_id="reliance",
        url="https://example.com/reliance/annual-report",
        source_type="company_ir",
        label="Annual report",
        verification_status="verified",
        verified_by="audit-team",
    )

    assert registry.get_company_by_symbol("reliance") == registry.get_company("reliance")
    assert registry.get_source_by_url(
        company_id="reliance",
        url="https://example.com/reliance/annual-report",
    ) is not None

    source_list = registry.list_sources(
        company_id="reliance",
        source_type="company_ir",
        verification_status="verified",
    )
    assert len(source_list) == 1
    assert source_list[0]["label"] == "Annual report"

    updated = registry.upsert_source(
        company_id="reliance",
        url="https://example.com/reliance/annual-report",
        source_type="company_ir",
        label="Annual report revised",
        verification_status="verified",
        verified_by="audit-team",
    )
    assert updated["label"] == "Annual report revised"
