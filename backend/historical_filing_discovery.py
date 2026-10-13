
import time
from pathlib import Path

import pandas as pd
import requests


BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data" / "company_discovery"

COMPANY_CATALOGUE = DATA_DIR / "company_catalogue.csv"
OUTPUT_FILE = DATA_DIR / "historical_filing_catalogue.csv"
ERROR_FILE = DATA_DIR / "discovery_errors.csv"

NSE_BASE_URL = "https://www.nseindia.com"
NSE_PAGE_URL = (
    NSE_BASE_URL
    + "/companies-listing/corporate-filings-annual-reports"
)
NSE_API_URL = NSE_BASE_URL + "/api/annual-reports"

# Pilot only. We will increase this after testing.
PILOT_COMPANY_LIMIT = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": NSE_PAGE_URL,
    "Origin": NSE_BASE_URL,
}


def main():
    if not COMPANY_CATALOGUE.is_file():
        raise FileNotFoundError(
            f"Company catalogue not found: {COMPANY_CATALOGUE}"
        )

    companies = pd.read_csv(
        COMPANY_CATALOGUE,
        dtype=str,
        keep_default_na=False,
    )

    required_columns = {"symbol", "company_name"}
    if not required_columns.issubset(companies.columns):
        raise ValueError(
            f"Catalogue must contain: {required_columns}"
        )

    companies = companies[
        (companies["symbol"].str.strip() != "")
        & (companies["company_name"].str.strip() != "")
    ].drop_duplicates(subset=["symbol"])

    # Include Reliance as a known test case, followed by other symbols.
    reliance = companies[
        companies["symbol"].str.upper() == "RELIANCE"
    ]
    others = companies[
        companies["symbol"].str.upper() != "RELIANCE"
    ]

    pilot = pd.concat([reliance, others]).head(
        PILOT_COMPANY_LIMIT
    )

    if pilot.empty:
        raise ValueError("No companies found in the catalogue.")

    session = requests.Session()
    session.headers.update(HEADERS)

    print("Opening official NSE annual-report page...")
    page = session.get(NSE_PAGE_URL, timeout=30)
    page.raise_for_status()

    all_records = []
    errors = []

    for number, (_, company) in enumerate(
        pilot.iterrows(), start=1
    ):
        symbol = company["symbol"].strip()
        company_name = company["company_name"].strip()

        print(
            f"\n[{number}/{len(pilot)}] "
            f"{symbol} — {company_name}"
        )

        try:
            response = session.get(
                NSE_API_URL,
                params={
                    "index": "equities",
                    "symbol": symbol,
                },
                timeout=30,
            )
            response.raise_for_status()

            payload = response.json()
            records = payload.get("data", [])

            if not isinstance(records, list):
                raise ValueError(
                    "Unexpected API response: 'data' is not a list."
                )

            print(f"Annual-report records: {len(records)}")

            for record in records:
                all_records.append({
                    "symbol": symbol,
                    "catalogue_company_name": company_name,
                    "reported_company_name": record.get(
                        "companyName", ""
                    ),
                    "from_year": record.get("fromYr", ""),
                    "to_year": record.get("toYr", ""),
                    "submission_type": record.get(
                        "submission_type", ""
                    ),
                    "broadcast_datetime": record.get(
                        "broadcast_dttm", ""
                    ),
                    "dissemination_datetime": record.get(
                        "disseminationDateTime", ""
                    ),
                    "attachment_url": record.get("fileName", ""),
                    "reported_file_size": record.get(
                        "attFileSize", ""
                    ),
                    "source": "NSE India",
                    "source_api": response.url,
                })

        except (
            requests.RequestException,
            ValueError,
            TypeError,
        ) as exc:
            print(f"ERROR: {exc}")
            errors.append({
                "symbol": symbol,
                "company_name": company_name,
                "error": str(exc),
            })

        # Avoid sending requests too quickly.
        time.sleep(1.5)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "symbol",
        "catalogue_company_name",
        "reported_company_name",
        "from_year",
        "to_year",
        "submission_type",
        "broadcast_datetime",
        "dissemination_datetime",
        "attachment_url",
        "reported_file_size",
        "source",
        "source_api",
    ]

    result = pd.DataFrame(all_records, columns=columns)

    if not result.empty:
        result = result.drop_duplicates(
            subset=["symbol", "from_year", "to_year",
                    "attachment_url"],
            keep="first",
        )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(errors).to_csv(
        ERROR_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 50)
    print("PILOT COMPLETED")
    print(f"Companies checked: {len(pilot)}")
    print(f"Filing records saved: {len(result)}")
    print(f"Companies with errors: {len(errors)}")
    print(f"Filing catalogue: {OUTPUT_FILE}")
    print(f"Error log: {ERROR_FILE}")

    if not result.empty:
        print("\nRecords per company:")
        print(
            result.groupby("symbol").size()
            .sort_values(ascending=False)
            .to_string()
        )

        print("\nSample records:")
        print(
            result[
                ["symbol", "from_year", "to_year",
                 "submission_type", "attachment_url"]
            ].head(10).to_string(index=False)
        )

    print(
        "\nNo PDFs or ZIP files were downloaded. "
        "Existing RAG files were not changed."
    )


if __name__ == "__main__":
    main()
