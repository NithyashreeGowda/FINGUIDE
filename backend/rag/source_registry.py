from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = (
    BACKEND_DIR
    / "data"
    / "company_discovery"
    / "financial_registry.json"
)

SCHEMA_VERSION = 1
SOURCE_TYPES = {
    "company_ir",
    "official_exchange",
    "official_regulator",
    "other",
}
VERIFICATION_STATUSES = {"unverified", "verified"}


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    return _required_text(value, field)


def _https_url(value: Any, field: str) -> str:
    url = _required_text(value, field)
    parts = urlsplit(url)

    if (
        parts.scheme.lower() != "https"
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError(f"{field} must be a valid HTTPS URL.")

    return urlunsplit(
        (
            "https",
            parts.netloc,
            parts.path,
            parts.query,
            "",
        )
    )


def _company_id(value: Any) -> str:
    company_id = _required_text(value, "company_id").lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", company_id):
        raise ValueError(
            "company_id may contain lowercase letters, numbers, "
            "hyphens, and underscores."
        )
    return company_id


def _company_symbol(value: Any) -> str | None:
    if value is None:
        return None
    symbol = _optional_text(value, "symbol")
    if symbol is None:
        return None
    return symbol.upper()


def _source_id(company_id: str, url: str) -> str:
    digest = hashlib.sha256(
        f"{company_id}\n{url}".encode("utf-8")
    ).hexdigest()
    return digest


class FinancialSourceRegistry:
    """JSON-backed registry; it does not fetch or verify source URLs."""

    def __init__(self, path: str | Path = DEFAULT_REGISTRY_PATH):
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": SCHEMA_VERSION,
                "companies": {},
                "sources": {},
            }

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Could not read registry file {self.path}: {exc}"
            ) from exc

        if (
            not isinstance(data, dict)
            or data.get("schema_version") != SCHEMA_VERSION
            or not isinstance(data.get("companies"), dict)
            or not isinstance(data.get("sources"), dict)
        ):
            raise ValueError(
                f"Registry file has an invalid schema: {self.path}"
            )

        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as exc:
            raise RuntimeError(
                f"Could not save registry file {self.path}: {exc}"
            ) from exc

    def register_company(
        self,
        *,
        company_id: str,
        name: str,
        country: str,
        symbol: str | None = None,
        exchange: str | None = None,
        sector: str | None = None,
        official_website: str | None = None,
        investor_relations_url: str | None = None,
        filing_source_urls: list[str] | None = None,
        document_categories: list[str] | None = None,
    ) -> dict[str, Any]:
        company_id = _company_id(company_id)
        name = _required_text(name, "name")
        country = _required_text(country, "country")

        urls = filing_source_urls or []
        if not isinstance(urls, list):
            raise TypeError("filing_source_urls must be a list.")

        categories = document_categories or []
        if not isinstance(categories, list):
            raise TypeError("document_categories must be a list.")

        company = {
            "company_id": company_id,
            "name": name,
            "symbol": _company_symbol(symbol),
            "exchange": _optional_text(exchange, "exchange"),
            "country": country,
            "sector": _optional_text(sector, "sector"),
            "official_website": (
                _https_url(official_website, "official_website")
                if official_website
                else None
            ),
            "investor_relations_url": (
                _https_url(
                    investor_relations_url,
                    "investor_relations_url",
                )
                if investor_relations_url
                else None
            ),
            "filing_source_urls": [
                _https_url(url, "filing_source_urls item")
                for url in urls
            ],
            "document_categories": [
                _required_text(item, "document_categories item")
                for item in categories
            ],
        }

        data = self._read()
        if company_id in data["companies"]:
            raise ValueError(
                f"Company already exists: {company_id}"
            )

        data["companies"][company_id] = company
        self._write(data)
        return company

    def register_source(
        self,
        *,
        company_id: str,
        url: str,
        source_type: str,
        label: str,
        verification_status: str = "unverified",
        verified_by: str | None = None,
    ) -> dict[str, Any]:
        company_id = _company_id(company_id)
        url = _https_url(url, "url")
        source_type = _required_text(
            source_type, "source_type"
        ).lower()
        verification_status = _required_text(
            verification_status, "verification_status"
        ).lower()

        if source_type not in SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(SOURCE_TYPES)}."
            )
        if verification_status not in VERIFICATION_STATUSES:
            raise ValueError(
                "verification_status must be 'unverified' or "
                "'verified'."
            )
        if verification_status == "verified" and not verified_by:
            raise ValueError(
                "verified_by is required when marking a source verified."
            )

        source = {
            "source_id": _source_id(company_id, url),
            "company_id": company_id,
            "url": url,
            "source_type": source_type,
            "label": _required_text(label, "label"),
            "verification_status": verification_status,
            "verified_by": _optional_text(verified_by, "verified_by"),
        }

        data = self._read()
        if company_id not in data["companies"]:
            raise ValueError(
                f"Register the company before its sources: {company_id}"
            )
        if source["source_id"] in data["sources"]:
            raise ValueError(
                f"Source already exists for this company and URL: {url}"
            )

        data["sources"][source["source_id"]] = source
        self._write(data)
        return source

    def list_companies(self) -> list[dict[str, Any]]:
        data = self._read()
        return list(data["companies"].values())

    def list_sources(
        self,
        *,
        company_id: str | None = None,
        verified_only: bool = False,
        source_type: str | None = None,
        verification_status: str | None = None,
    ) -> list[dict[str, Any]]:
        data = self._read()
        sources = list(data["sources"].values())

        if company_id is not None:
            company_id = _company_id(company_id)
            sources = [
                source
                for source in sources
                if source["company_id"] == company_id
            ]

        if source_type is not None:
            source_type = _required_text(source_type, "source_type").lower()
            sources = [
                source
                for source in sources
                if source["source_type"] == source_type
            ]

        if verification_status is not None:
            verification_status = _required_text(
                verification_status,
                "verification_status",
            ).lower()
            sources = [
                source
                for source in sources
                if source["verification_status"] == verification_status
            ]

        if verified_only:
            sources = [
                source
                for source in sources
                if source["verification_status"] == "verified"
            ]

        return sources

    def get_company(self, company_id: str) -> dict[str, Any] | None:
        data = self._read()
        return data["companies"].get(_company_id(company_id))

    def get_company_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        normalized = _company_symbol(symbol)
        if normalized is None:
            return None

        data = self._read()
        for company in data["companies"].values():
            if (company.get("symbol") or "").upper() == normalized:
                return company
        return None

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        data = self._read()
        return data["sources"].get(source_id)

    def get_source_by_url(
        self,
        *,
        company_id: str,
        url: str,
    ) -> dict[str, Any] | None:
        data = self._read()
        company_id = _company_id(company_id)
        url = _https_url(url, "url")
        return data["sources"].get(_source_id(company_id, url))

    def upsert_company(
        self,
        *,
        company_id: str,
        name: str,
        country: str,
        symbol: str | None = None,
        exchange: str | None = None,
        sector: str | None = None,
        official_website: str | None = None,
        investor_relations_url: str | None = None,
        filing_source_urls: list[str] | None = None,
        document_categories: list[str] | None = None,
    ) -> dict[str, Any]:
        company_id = _company_id(company_id)
        data = self._read()

        if company_id not in data["companies"]:
            return self.register_company(
                company_id=company_id,
                name=name,
                country=country,
                symbol=symbol,
                exchange=exchange,
                sector=sector,
                official_website=official_website,
                investor_relations_url=investor_relations_url,
                filing_source_urls=filing_source_urls,
                document_categories=document_categories,
            )

        existing = data["companies"][company_id]
        updated = {
            "company_id": company_id,
            "name": _required_text(name, "name"),
            "country": _required_text(country, "country"),
            "symbol": (
                _company_symbol(symbol)
                if symbol is not None
                else existing.get("symbol")
            ),
            "exchange": _optional_text(exchange, "exchange")
            if exchange is not None
            else existing.get("exchange"),
            "sector": _optional_text(sector, "sector")
            if sector is not None
            else existing.get("sector"),
            "official_website": (
                _https_url(official_website, "official_website")
                if official_website is not None
                else existing.get("official_website")
            ),
            "investor_relations_url": (
                _https_url(
                    investor_relations_url,
                    "investor_relations_url",
                )
                if investor_relations_url is not None
                else existing.get("investor_relations_url")
            ),
            "filing_source_urls": (
                [
                    _https_url(url, "filing_source_urls item")
                    for url in filing_source_urls
                ]
                if filing_source_urls is not None
                else existing.get("filing_source_urls", [])
            ),
            "document_categories": (
                [
                    _required_text(item, "document_categories item")
                    for item in document_categories
                ]
                if document_categories is not None
                else existing.get("document_categories", [])
            ),
        }
        data["companies"][company_id] = {**existing, **updated}
        self._write(data)
        return data["companies"][company_id]

    def upsert_source(
        self,
        *,
        company_id: str,
        url: str,
        source_type: str,
        label: str,
        verification_status: str = "unverified",
        verified_by: str | None = None,
    ) -> dict[str, Any]:
        company_id = _company_id(company_id)
        data = self._read()

        if company_id not in data["companies"]:
            raise ValueError(
                f"Register the company before its sources: {company_id}"
            )

        source_key = _source_id(company_id, _https_url(url, "url"))
        if source_key not in data["sources"]:
            return self.register_source(
                company_id=company_id,
                url=url,
                source_type=source_type,
                label=label,
                verification_status=verification_status,
                verified_by=verified_by,
            )

        existing = data["sources"][source_key]
        updated = {
            "source_id": source_key,
            "company_id": company_id,
            "url": _https_url(url, "url"),
            "source_type": _required_text(
                source_type, "source_type"
            ).lower(),
            "label": _required_text(label, "label"),
            "verification_status": _required_text(
                verification_status, "verification_status"
            ).lower(),
            "verified_by": _optional_text(verified_by, "verified_by"),
        }
        if updated["verification_status"] == "verified" and not updated["verified_by"]:
            raise ValueError(
                "verified_by is required when marking a source verified."
            )

        if updated["source_type"] not in SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(SOURCE_TYPES)}."
            )
        if updated["verification_status"] not in VERIFICATION_STATUSES:
            raise ValueError(
                "verification_status must be 'unverified' or 'verified'."
            )

        data["sources"][source_key] = {**existing, **updated}
        self._write(data)
        return data["sources"][source_key]