from pathlib import Path
from io import BytesIO
from datetime import datetime, timezone

import pandas as pd
import requests


# Project paths
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data" / "company_discovery"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Official NSE equity securities CSV
NSE_CSV_URL = (
    "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,*/*",
    "Referer": (
        "https://www.nseindia.com/"
        "static/market-data/securities-available-for-trading"
    ),
}


def find_column(columns, candidates):
    """Find a column using normalized column names."""
    normalized = {
        str(column).strip().upper(): column
        for column in columns
    }

    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]

    return None


def main():
    print("FinGuide: Official Company Discovery")
    print("-" * 45)
    print("Source: NSE India equity securities list")

    try:
        response = requests.get(
            NSE_CSV_URL,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        # Parse the CSV downloaded from the official NSE archive.
        df = pd.read_csv(
            BytesIO(response.content),
            encoding="utf-8-sig",
            dtype=str,
        )

        if df.empty:
            raise ValueError("The downloaded NSE CSV is empty.")

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        symbol_column = find_column(
            df.columns,
            ["SYMBOL", "TCKR"],
        )

        name_column = find_column(
            df.columns,
            [
                "NAME OF COMPANY",
                "COMPANY NAME",
                "NAME",
            ],
        )

        if symbol_column is None or name_column is None:
            raise ValueError(
                "Could not identify the company symbol and name "
                f"columns. Columns received: {list(df.columns)}"
            )

        # Keep rows with both a symbol and company name.
        df[symbol_column] = df[symbol_column].fillna("").str.strip()
        df[name_column] = df[name_column].fillna("").str.strip()

        df = df[
            (df[symbol_column] != "")
            & (df[name_column] != "")
        ].copy()

        df = df.drop_duplicates(
            subset=[symbol_column],
            keep="first",
        )

        # Preserve the original exchange fields in the catalogue.
        df = df.rename(
            columns={
                symbol_column: "symbol",
                name_column: "company_name",
            }
        )

        df["discovery_source"] = "NSE India"
        df["source_url"] = NSE_CSV_URL
        df["discovered_at_utc"] = datetime.now(
            timezone.utc
        ).isoformat()

        # Save the normalized company catalogue.
        catalogue_path = DATA_DIR / "company_catalogue.csv"
        df.to_csv(catalogue_path, index=False, encoding="utf-8-sig")

        # Save the exact downloaded source for traceability.
        raw_path = DATA_DIR / "nse_equity_securities_raw.csv"
        raw_path.write_bytes(response.content)

        print("\nDiscovery successful.")
        print(f"Companies/securities catalogued: {len(df)}")
        print(f"Catalogue: {catalogue_path}")
        print(f"Original CSV: {raw_path}")

        print("\nFirst 10 entries:")
        print(
            df[["symbol", "company_name"]]
            .head(10)
            .to_string(index=False)
        )

    except requests.RequestException as exc:
        print("\nCould not download the NSE CSV.")
        print("Check your internet connection and try again.")
        print(f"Details: {exc}")

    except (ValueError, pd.errors.ParserError) as exc:
        print("\nCould not process the NSE CSV.")
        print(f"Details: {exc}")


if __name__ == "__main__":
    main()