from pathlib import Path
from datetime import datetime
import pymupdf


SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": "financial_report",
}


def extract_pdf_text(file_path: str) -> list[dict]:
    """
    Extract text from every page of a PDF.

    Returns:
        A list containing page-level extracted text.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF documents are currently supported.")

    pages = []

    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=True).strip()

            if text:
                pages.append(
                    {
                        "page": page_number,
                        "text": text,
                    }
                )

    return pages


def load_financial_document(
    file_path: str,
    source: str | None = None,
    company: str | None = None,
    document_type: str | None = None,
    document_date: str | None = None,
) -> dict:
    """
    Load a financial PDF and attach evidence metadata.

    Metadata follows the project's Person 2 specification:
        text
        source
        date
        company
        document_type
    """

    path = Path(file_path)

    pages = extract_pdf_text(str(path))

    if not pages:
        raise ValueError(
            "No extractable text was found in the PDF."
        )

    if document_type is None:
        document_type = SUPPORTED_DOCUMENT_TYPES.get(
            path.suffix.lower(),
            "financial_document",
        )

    if document_date is None:
        document_date = datetime.now().date().isoformat()

    evidence = []

    for page_data in pages:
        evidence.append(
            {
                "text": page_data["text"],
                "source": source or path.name,
                "date": document_date,
                "company": company,
                "document_type": document_type,
                "page": page_data["page"],
                "file_name": path.name,
            }
        )

    return {
        "file_name": path.name,
        "source": source or path.name,
        "date": document_date,
        "company": company,
        "document_type": document_type,
        "page_count": len(pages),
        "evidence": evidence,
    }