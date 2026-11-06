from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests


BACKEND_DIR = Path(__file__).resolve().parent
COMPANY_DATA_DIR = BACKEND_DIR / "data" / "company_discovery"
NIFTY500_SOURCE_URL = (
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
)
DEFAULT_CONSTITUENTS_PATH = COMPANY_DATA_DIR / "nifty500_constituents.csv"
DEFAULT_MASTER_PATH = COMPANY_DATA_DIR / "nifty500_company_master.json"
MASTER_SCHEMA_VERSION = 1
MAX_CONSTITUENT_FILE_BYTES = 2 * 1024 * 1024
OFFICIAL_SOURCE_HOSTS = {"niftyindices.com", "www.niftyindices.com"}


def _official_source_url(value: str) -> str:
    parts = urlsplit(value)
    if (
        parts.scheme.lower() != "https"
        or parts.hostname not in OFFICIAL_SOURCE_HOSTS
        or parts.username
        or parts.password
        or parts.path != "/IndexConstituent/ind_nifty500list.csv"
        or parts.query
        or parts.fragment
        or parts.port not in (None, 443)
    ):
        raise ValueError("The company-universe source must be the official Nifty Indices HTTPS site.")
    return value


def _verified_timestamp(value: str | datetime | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("verified_at must be an ISO-8601 datetime.") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("verified_at must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat()


def _company_id(symbol: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", symbol.strip().lower()).strip("-")
    if not normalized or not re.match(r"[a-z0-9]", normalized):
        raise ValueError(f"Cannot create a stable company ID for symbol: {symbol!r}")
    return normalized


def parse_nifty500_constituents(
    csv_content: bytes,
    *,
    source_url: str = NIFTY500_SOURCE_URL,
    verified_at: str | datetime | None = None,
) -> dict[str, Any]:
    """Parse and validate the official NIFTY 500 constituent CSV."""
    source_url = _official_source_url(source_url)
    verification_time = _verified_timestamp(verified_at)

    if not isinstance(csv_content, bytes) or not csv_content:
        raise ValueError("The NIFTY 500 constituent file is empty.")
    if len(csv_content) > MAX_CONSTITUENT_FILE_BYTES:
        raise ValueError("The NIFTY 500 constituent file exceeds the size limit.")

    try:
        text = csv_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The NIFTY 500 constituent file must be UTF-8 CSV.") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("The NIFTY 500 file has no CSV header.")

    header_lookup = {
        re.sub(r"\s+", " ", name.strip()).casefold(): name
        for name in reader.fieldnames
        if name
    }
    required_headers = {
        "company name": "company_name",
        "industry": "industry",
        "symbol": "symbol",
        "series": "series",
        "isin code": "isin",
    }
    missing = [
        header
        for header in required_headers
        if header not in header_lookup
    ]
    if missing:
        raise ValueError(
            "The NIFTY 500 CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    source_hash = hashlib.sha256(csv_content).hexdigest()
    companies: list[dict[str, Any]] = []
    seen_symbols: set[str] = set()
    seen_company_ids: set[str] = set()

    for row_number, row in enumerate(reader, start=2):
        company_name = (row.get(header_lookup["company name"]) or "").strip()
        industry = (row.get(header_lookup["industry"]) or "").strip()
        symbol = (row.get(header_lookup["symbol"]) or "").strip().upper()
        series = (row.get(header_lookup["series"]) or "").strip().upper()
        isin = (row.get(header_lookup["isin code"]) or "").strip().upper() or None

        if not company_name or not symbol:
            raise ValueError(
                f"NIFTY 500 row {row_number} has no company name or symbol."
            )
        if symbol in seen_symbols:
            raise ValueError(f"Duplicate NIFTY 500 symbol at row {row_number}: {symbol}")
        seen_symbols.add(symbol)

        company_id = _company_id(symbol)
        if company_id in seen_company_ids:
            raise ValueError(
                f"NIFTY 500 symbols produce a duplicate company ID at row {row_number}: {symbol}"
            )
        seen_company_ids.add(company_id)

        if isin and not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", isin):
            raise ValueError(f"Invalid ISIN at NIFTY 500 row {row_number}: {isin}")

        verified_fields = [
            "name",
            "symbol",
            "exchange",
            "listing_status",
            "index_memberships",
        ]
        if industry:
            verified_fields.append("industry")
        if isin:
            verified_fields.append("isin")
        if series:
            verified_fields.append("listing_series")

        companies.append({
            "company_id": company_id,
            "name": company_name,
            "country": "India",
            "symbol": symbol,
            "nse_symbol": symbol,
            "bse_code": None,
            "isin": isin,
            "cin": None,
            "sector": None,
            "industry": industry or None,
            "official_website": None,
            "investor_relations_url": None,
            "exchange": "NSE",
            "listing_status": "listed",
            "listing_series": series or None,
            "index_memberships": ["NIFTY 500"],
            "source_verified_at": verification_time,
            "metadata_source_url": source_url,
            "metadata_source_sha256": source_hash,
            "source_verification_status": "verified",
            "verified_fields": verified_fields,
        })

    if not companies:
        raise ValueError("The NIFTY 500 constituent file contains no company records.")

    return {
        "schema_version": MASTER_SCHEMA_VERSION,
        "index_name": "NIFTY 500",
        "source_organization": "NSE Indices",
        "source_url": source_url,
        "source_sha256": source_hash,
        "source_verified_at": verification_time,
        "constituent_count": len(companies),
        "companies": companies,
    }


class Nifty500CompanyMaster:
    """Source-backed company master populated from the official index CSV."""

    def __init__(
        self,
        *,
        master_path: str | Path = DEFAULT_MASTER_PATH,
        constituents_path: str | Path = DEFAULT_CONSTITUENTS_PATH,
    ):
        self.master_path = Path(master_path)
        self.constituents_path = Path(constituents_path)

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary_path.write_bytes(content)
            os.replace(temporary_path, path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Could not save company master file {path}: {exc}") from exc

    def refresh_from_csv(
        self,
        csv_content: bytes,
        *,
        source_url: str = NIFTY500_SOURCE_URL,
        verified_at: str | datetime | None = None,
    ) -> dict[str, Any]:
        data = parse_nifty500_constituents(
            csv_content,
            source_url=source_url,
            verified_at=verified_at,
        )
        serialized = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        self._atomic_write(self.constituents_path, csv_content)
        self._atomic_write(self.master_path, serialized)
        return {
            "constituent_count": data["constituent_count"],
            "verified_count": sum(
                company["source_verification_status"] == "verified"
                for company in data["companies"]
            ),
            "source_url": data["source_url"],
            "source_sha256": data["source_sha256"],
            "source_verified_at": data["source_verified_at"],
            "master_path": str(self.master_path),
            "constituents_path": str(self.constituents_path),
        }

    def refresh_from_official_source(self) -> dict[str, Any]:
        response = requests.get(
            NIFTY500_SOURCE_URL,
            headers={
                "User-Agent": "FinGuide company master importer/1.0",
                "Accept": "text/csv,application/octet-stream;q=0.9,*/*;q=0.1",
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.content
        if len(content) > MAX_CONSTITUENT_FILE_BYTES:
            raise ValueError("The NIFTY 500 constituent file exceeds the size limit.")
        return self.refresh_from_csv(content, source_url=response.url)

    def _read(self) -> dict[str, Any]:
        if not self.master_path.is_file():
            raise FileNotFoundError(f"Company master not found: {self.master_path}")
        try:
            data = json.loads(self.master_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not read company master {self.master_path}: {exc}") from exc

        companies = data.get("companies") if isinstance(data, dict) else None
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != MASTER_SCHEMA_VERSION
            or not isinstance(companies, list)
            or data.get("constituent_count") != len(companies)
            or not all(isinstance(company, dict) for company in companies)
        ):
            raise ValueError(f"Company master has an invalid schema: {self.master_path}")

        symbols = [company.get("symbol") for company in companies]
        if any(not isinstance(symbol, str) or not symbol for symbol in symbols):
            raise ValueError(f"Company master contains a missing symbol: {self.master_path}")
        if len(symbols) != len(set(symbols)):
            raise ValueError(f"Company master contains duplicate symbols: {self.master_path}")
        return data

    def list_companies(self) -> list[dict[str, Any]]:
        return self._read()["companies"]

    def get_company_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol must be a non-empty string.")
        normalized = symbol.strip().upper()
        for company in self.list_companies():
            if company["symbol"].upper() == normalized:
                return company
        return None

    def summary(self) -> dict[str, Any]:
        data = self._read()
        companies = data["companies"]
        return {
            "index_name": data["index_name"],
            "constituent_count": len(companies),
            "verified_count": sum(
                company.get("source_verification_status") == "verified"
                for company in companies
            ),
            "source_url": data["source_url"],
            "source_sha256": data["source_sha256"],
            "source_verified_at": data["source_verified_at"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh the company master from the official NIFTY 500 constituent CSV."
    )
    parser.parse_args()
    summary = Nifty500CompanyMaster().refresh_from_official_source()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
