
import csv
import json
import re
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf


SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": "financial_report",
    ".txt": "financial_text",
    ".csv": "financial_table",
    ".md": "financial_markdown",
    ".json": "financial_json",
    ".xml": "financial_xml",
    ".xbrl": "financial_xbrl",
    ".html": "financial_html",
    ".htm": "financial_html",
    ".docx": "financial_document",
    ".xlsx": "financial_table",
    ".pptx": "financial_presentation",
    ".xls": "financial_table",
    ".doc": "financial_document",
}


def _normalize_text(value: str) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return re.sub(r"\s+", " ", text).strip()


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def _extract_text_from_json(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = []

    def walk(value, prefix=""):
        if isinstance(value, dict):
            for key, item in value.items():
                next_prefix = f"{prefix} {key}" if prefix else str(key)
                walk(item, next_prefix)
        elif isinstance(value, list):
            for item in value:
                walk(item, prefix)
        elif value is not None:
            chunks.append(str(value))

    walk(data)
    return "\n".join(chunks)


def _extract_text_from_csv(path: Path) -> str:
    rows = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if row:
                rows.append(" | ".join(cell.strip() for cell in row if cell and cell.strip()))
    return "\n".join(rows)


def _extract_text_from_xml(path: Path) -> str:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return _read_text_file(path)

    chunks = []
    for node in root.iter():
        value = (node.text or "").strip()
        if value:
            chunks.append(value)
    return "\n".join(chunks)


def _extract_text_from_xbrl(path: Path) -> str:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return _read_text_file(path)

    chunks: list[str] = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in {"context", "unit", "schemaRef", "linkbaseRef"}:
            continue

        text = (node.text or "").strip()
        if text:
            chunks.append(f"{tag}: {text}")

        for key, value in node.attrib.items():
            if key in {"contextRef", "unitRef", "decimals", "id", "name"}:
                chunks.append(f"{tag} {key}: {value}")

    return "\n".join(chunks) if chunks else _extract_text_from_xml(path)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        text = _normalize_text(data)
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self.parts)


def _extract_text_from_html(path: Path) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(_read_text_file(path))
    parser.close()
    return parser.get_text()


def _extract_text_from_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_text = archive.read("word/document.xml")
    root = ET.fromstring(xml_text)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(
            node.text or ""
            for node in paragraph.findall(".//w:t", ns)
        )
        if text.strip():
            chunks.append(text.strip())
    return "\n".join(chunks)


def _extract_text_from_xlsx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for node in root.findall(".//a:si", ns):
                text = "".join(t.text or "" for t in node.iterfind(".//a:t", ns))
                shared_strings.append(text)

        chunks = []
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        for sheet_name in archive.namelist():
            if not sheet_name.startswith("xl/worksheets/") or not sheet_name.endswith(".xml"):
                continue
            root = ET.fromstring(archive.read(sheet_name))
            for row in root.findall(".//a:sheetData/a:row", ns):
                values = []
                for cell in row.findall("a:c", ns):
                    cell_type = cell.get("t")
                    value = ""
                    if cell_type == "s":
                        idx = int((cell.find("a:v", ns).text or "0"))
                        value = shared_strings[idx] if idx < len(shared_strings) else ""
                    else:
                        value = (cell.findtext("a:v", default="", namespaces=ns) or "")
                    if value:
                        values.append(value)
                if values:
                    chunks.append(" | ".join(values))
        return "\n".join(chunks)


def _extract_text_from_pptx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        chunks = []
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
        for name in archive.namelist():
            if not name.startswith("ppt/slides/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(archive.read(name))
            for node in root.iter():
                text = "".join(t.text or "" for t in node.findall(".//a:t", ns))
                if text.strip():
                    chunks.append(text.strip())
        return "\n".join(chunks)


def _extract_text_from_zip(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        content = []
        for member in archive.namelist():
            if member.endswith("/"):
                continue
            member_path = Path(member)
            if member_path.suffix.lower() in SUPPORTED_DOCUMENT_TYPES:
                inner_file = archive.extract(member, path=path.parent)
                try:
                    content.append(extract_text_from_file(inner_file))
                finally:
                    Path(inner_file).unlink(missing_ok=True)
        return "\n".join(content)


def extract_text_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages = extract_pdf_text(str(path))
        return "\n\n".join(page["text"] for page in pages)
    if suffix in {".txt", ".md", ".html", ".htm", ".xml", ".xbrl"}:
        if suffix in {".html", ".htm"}:
            return _extract_text_from_html(path)
        if suffix == ".xml":
            return _extract_text_from_xml(path)
        if suffix == ".xbrl":
            return _extract_text_from_xbrl(path)
        return _normalize_text(_read_text_file(path))
    if suffix == ".csv":
        return _extract_text_from_csv(path)
    if suffix == ".json":
        return _extract_text_from_json(path)
    if suffix == ".docx":
        return _extract_text_from_docx(path)
    if suffix in {".xlsx", ".xls"}:
        return _extract_text_from_xlsx(path)
    if suffix == ".pptx":
        return _extract_text_from_pptx(path)
    if suffix == ".zip":
        return _extract_text_from_zip(path)
    raise ValueError(f"Unsupported financial document type: {suffix or path.name}")


def extract_pdf_text(file_path: str) -> list[dict]:
    """
    Extract text from every page of a PDF.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF documents are supported by the PDF extractor.")

    pages = []

    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=True).strip()
            if text:
                pages.append({"page": page_number, "text": text})

    return pages


def load_financial_document(
    file_path: str,
    source: str | None = None,
    company: str | None = None,
    document_type: str | None = None,
    document_date: str | None = None,
    source_url: str | None = None,
    symbol: str | None = None,
    financial_year: str | None = None,
    reporting_period: str | None = None,
    scope: str | None = None,
    publication_date: str | None = None,
    source_organization: str | None = None,
    verification_status: str | None = None,
) -> dict:
    """
    Load a financial document and attach structured evidence metadata.
    """

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = extract_pdf_text(str(path))
    else:
        extracted_text = extract_text_from_file(path)
        if not extracted_text.strip():
            raise ValueError("No extractable text was found in the document.")
        pages = [{"page": 1, "text": extracted_text}]

    if not pages:
        raise ValueError("No extractable text was found in the document.")

    if document_type is None:
        document_type = SUPPORTED_DOCUMENT_TYPES.get(
            path.suffix.lower(),
            "financial_document",
        )

    if document_date is not None:
        document_date = str(document_date).strip() or None

    document_hash = sha256(path.read_bytes()).hexdigest()
    document_id = document_hash
    ingestion_timestamp = datetime.now(timezone.utc).isoformat()
    document_source = source or path.name

    preserved_metadata = {
        "symbol": symbol,
        "financial_year": financial_year,
        "reporting_period": reporting_period,
        "scope": scope,
        "publication_date": publication_date,
        "source_organization": source_organization,
        "verification_status": verification_status,
    }

    evidence = []
    for page_data in pages:
        record = {
            "text": page_data["text"],
            "source": document_source,
            "source_url": source_url,
            "date": document_date,
            "company": company,
            "document_type": document_type,
            "page": page_data["page"],
            "file_name": path.name,
            "document_id": document_id,
            "ingestion_timestamp": ingestion_timestamp,
        }
        record.update({
            key: value
            for key, value in preserved_metadata.items()
            if value is not None
        })
        evidence.append(record)

    result = {
        "file_name": path.name,
        "source": document_source,
        "source_url": source_url,
        "date": document_date,
        "company": company,
        "document_type": document_type,
        "document_id": document_id,
        "ingestion_timestamp": ingestion_timestamp,
        "page_count": len(pages),
        "evidence": evidence,
    }
    result.update({
        key: value
        for key, value in preserved_metadata.items()
        if value is not None
    })
    return result
