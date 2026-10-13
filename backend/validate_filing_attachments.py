
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile, BadZipFile
import hashlib
import time

import pandas as pd
import requests


BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data" / "company_discovery"
CATALOGUE = DATA_DIR / "historical_filing_catalogue.csv"

DOWNLOAD_DIR = (
    BACKEND_DIR / "data" / "financial_documents" / "incoming"
)
RESULT_FILE = DATA_DIR / "attachment_validation.csv"

MAX_FILES = 4
MAX_FILE_BYTES = 100 * 1024 * 1024  # 100 MB per sample

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Referer": (
        "https://www.nseindia.com/"
        "companies-listing/corporate-filings-annual-reports"
    ),
}


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def inspect_zip(path):
    """Inspect ZIP names without extracting any files."""
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]

            unsafe_names = [
                name for name in names
                if Path(name).is_absolute()
                or ".." in name.replace("\\", "/").split("/")
            ]

            return {
                "zip_valid": archive.testzip() is None,
                "zip_member_count": len(members),
                "zip_member_names_sample": " | ".join(names[:10]),
                "zip_unsafe_paths": len(unsafe_names),
            }

    except (BadZipFile, OSError) as error:
        return {
            "zip_valid": False,
            "zip_member_count": 0,
            "zip_member_names_sample": "",
            "zip_unsafe_paths": "",
            "zip_error": str(error),
        }


def main():
    if not CATALOGUE.is_file():
        raise FileNotFoundError(
            f"Catalogue not found: {CATALOGUE}"
        )

    df = pd.read_csv(
        CATALOGUE,
        dtype=str,
        keep_default_na=False,
    )

    df["extension"] = df["attachment_url"].apply(
        lambda url: Path(urlparse(url).path).suffix.lower()
    )

    # Test both formats where available.
    samples = []

    for extension in [".pdf", ".zip"]:
        candidates = df[
            (df["extension"] == extension)
            & (df["attachment_url"].str.startswith("https://"))
        ]

        if not candidates.empty:
            samples.append(candidates.iloc[0])

    # Add further distinct examples until reaching MAX_FILES.
    for _, record in df.iterrows():
        if len(samples) >= MAX_FILES:
            break

        if not record["attachment_url"].startswith("https://"):
            continue

        if any(
            record["attachment_url"] == item["attachment_url"]
            for item in samples
        ):
            continue

        samples.append(record)

    samples = samples[:MAX_FILES]

    if not samples:
        raise ValueError("No HTTPS attachment URLs were found.")

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    results = []

    for number, record in enumerate(samples, start=1):
        url = record["attachment_url"]
        extension = Path(urlparse(url).path).suffix.lower()
        symbol = record["symbol"]
        from_year = record["from_year"]
        to_year = record["to_year"]

        output = DOWNLOAD_DIR / (
            f"{symbol}_{from_year}_{to_year}{extension}"
        )

        result = {
            "symbol": symbol,
            "from_year": from_year,
            "to_year": to_year,
            "url": url,
            "expected_extension": extension,
            "download_success": False,
            "signature_valid": False,
            "sha256": "",
            "file_bytes": 0,
            "error": "",
        }

        print(
            f"\n[{number}/{len(samples)}] "
            f"{symbol}: {from_year}-{to_year} ({extension})"
        )

        try:
            digest = hashlib.sha256()
            total_bytes = 0
            first_bytes = b""

            with session.get(
                url,
                stream=True,
                timeout=(15, 60),
                allow_redirects=True,
            ) as response:
                result["http_status"] = response.status_code
                result["final_url"] = response.url
                response.raise_for_status()

                content_type = response.headers.get(
                    "Content-Type", ""
                )
                result["content_type"] = content_type

                with output.open("wb") as file:
                    for block in response.iter_content(
                        chunk_size=64 * 1024
                    ):
                        if not block:
                            continue

                        total_bytes += len(block)

                        if total_bytes > MAX_FILE_BYTES:
                            raise ValueError(
                                "File exceeded the 100 MB sample limit."
                            )

                        if len(first_bytes) < 8:
                            first_bytes += block[
                                :8 - len(first_bytes)
                            ]

                        digest.update(block)
                        file.write(block)

            result["file_bytes"] = total_bytes
            result["sha256"] = digest.hexdigest()
            result["download_success"] = total_bytes > 0

            if extension == ".pdf":
                result["signature_valid"] = (
                    first_bytes.startswith(b"%PDF-")
                )

            elif extension == ".zip":
                result["signature_valid"] = (
                    first_bytes.startswith(b"PK")
                )

                if result["signature_valid"]:
                    result.update(inspect_zip(output))

            print("HTTP status:", result.get("http_status"))
            print("Bytes downloaded:", total_bytes)
            print("Signature valid:", result["signature_valid"])
            print("SHA-256:", result["sha256"])

            if extension == ".zip":
                print(
                    "ZIP valid:",
                    result.get("zip_valid", False),
                )
                print(
                    "ZIP members:",
                    result.get("zip_member_count", 0),
                )
                print(
                    "Potential unsafe paths:",
                    result.get("zip_unsafe_paths", ""),
                )

        except (
            requests.RequestException,
            OSError,
            ValueError,
        ) as error:
            result["error"] = str(error)
            print("Validation error:", error)

            # Remove incomplete downloads.
            if output.exists():
                output.unlink()

        results.append(result)
        time.sleep(1.5)

    pd.DataFrame(results).to_csv(
        RESULT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 45)
    print("ATTACHMENT VALIDATION COMPLETE")
    print("Results:", RESULT_FILE)
    print("Sample files:", DOWNLOAD_DIR)
    print(
        "Existing FAISS index and metadata were not modified."
    )


if __name__ == "__main__":
    main()
