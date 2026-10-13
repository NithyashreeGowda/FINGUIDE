
from pathlib import Path

import fitz
import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parent
PDF_DIR = (
    BACKEND_DIR / "data" / "financial_documents" / "incoming"
)
OUTPUT_FILE = (
    BACKEND_DIR
    / "data"
    / "company_discovery"
    / "pdf_content_audit.csv"
)


def main():
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in: {PDF_DIR}")
        return

    results = []

    for pdf_path in pdf_files:
        print(f"\nChecking: {pdf_path.name}")

        result = {
            "file_name": pdf_path.name,
            "file_bytes": pdf_path.stat().st_size,
            "opens_successfully": False,
            "page_count": 0,
            "has_extractable_text": False,
            "mentions_reliance": False,
            "mentions_annual_report": False,
            "title": "",
            "error": "",
        }

        try:
            with fitz.open(pdf_path) as document:
                result["opens_successfully"] = True
                result["page_count"] = len(document)
                result["title"] = (
                    document.metadata.get("title", "") or ""
                )

                # Inspect a few pages first, not the entire document.
                sample_pages = list(document[:3])
                sample_text = "\n".join(
                    page.get_text("text")
                    for page in sample_pages
                ).lower()

                result["has_extractable_text"] = bool(
                    sample_text.strip()
                )
                result["mentions_reliance"] = (
                    "reliance" in sample_text
                )
                result["mentions_annual_report"] = (
                    "annual report" in sample_text
                    or "integrated report" in sample_text
                )

                print("Pages:", result["page_count"])
                print(
                    "Extractable text:",
                    result["has_extractable_text"],
                )
                print(
                    "Mentions Reliance:",
                    result["mentions_reliance"],
                )
                print(
                    "Mentions annual/integrated report:",
                    result["mentions_annual_report"],
                )
                print("PDF title:", result["title"] or "[not set]")

        except Exception as error:
            result["error"] = str(error)
            print("PDF inspection failed:", error)

        results.append(result)

    pd.DataFrame(results).to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nPDF content audit saved to:")
    print(OUTPUT_FILE)
    print("\nNote: this is an initial content check,")
    print("not proof of financial authenticity.")


if __name__ == "__main__":
    main()
