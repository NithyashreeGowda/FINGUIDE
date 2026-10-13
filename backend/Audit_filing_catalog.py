
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parent
CATALOGUE = (
    BACKEND_DIR
    / "data"
    / "company_discovery"
    / "historical_filing_catalogue.csv"
)


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

    if df.empty:
        print("The filing catalogue is empty.")
        return

    required = {
        "symbol",
        "from_year",
        "to_year",
        "submission_type",
        "attachment_url",
    }

    missing_columns = required - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    # Basic catalogue quality checks.
    df["from_year_num"] = pd.to_numeric(
        df["from_year"], errors="coerce"
    )
    df["to_year_num"] = pd.to_numeric(
        df["to_year"], errors="coerce"
    )

    df["attachment_url"] = df["attachment_url"].str.strip()

    df["valid_https_url"] = df["attachment_url"].apply(
        lambda url: urlparse(url).scheme == "https"
        and bool(urlparse(url).netloc)
    )

    df["file_extension"] = df["attachment_url"].apply(
        lambda url: Path(urlparse(url).path).suffix.lower()
        if url else ""
    )

    print("=" * 55)
    print("FinGuide Historical Filing Catalogue Audit")
    print("=" * 55)

    print(f"Total filing records: {len(df)}")
    print(f"Distinct company symbols: {df['symbol'].nunique()}")
    print(
        "Records with empty attachment URLs:",
        int((df["attachment_url"] == "").sum()),
    )
    print(
        "Records with HTTPS attachment URLs:",
        int(df["valid_https_url"].sum()),
    )
    print(
        "Records with non-HTTPS/invalid URLs:",
        int((~df["valid_https_url"]).sum()),
    )
    print(
        "Records with unrecognized year values:",
        int(
            (
                df["from_year_num"].isna()
                | df["to_year_num"].isna()
            ).sum()
        ),
    )

    print("\nAttachment extensions:")
    extensions = Counter(
        ext if ext else "[missing]"
        for ext in df["file_extension"]
    )
    for ext, count in extensions.most_common():
        print(f"  {ext}: {count}")

    # Detect repeated records for the same company and period.
    periods = df[
        df["from_year_num"].notna()
        & df["to_year_num"].notna()
    ]

    duplicate_periods = periods.duplicated(
        subset=["symbol", "from_year_num", "to_year_num"],
        keep=False,
    )

    print(
        "\nRecords belonging to repeated company/year periods:",
        int(duplicate_periods.sum()),
    )

    # Report available coverage by company.
    coverage = (
        df.groupby("symbol")
        .agg(
            filing_records=("symbol", "size"),
            first_from_year=("from_year_num", "min"),
            latest_to_year=("to_year_num", "max"),
            usable_urls=("valid_https_url", "sum"),
        )
        .reset_index()
    )

    coverage["observed_year_span"] = (
        coverage["latest_to_year"]
        - coverage["first_from_year"]
        + 1
    )

    coverage = coverage.sort_values(
        ["filing_records", "symbol"],
        ascending=[False, True],
    )

    output = CATALOGUE.parent / "pilot_coverage_audit.csv"
    coverage.to_csv(output, index=False, encoding="utf-8-sig")

    print("\nCoverage summary:")
    print(coverage.to_string(index=False))
    print(f"\nSaved coverage report: {output}")

    print(
        "\nNote: year span is only a rough range. "
        "It does not prove every year has a valid report."
    )


if __name__ == "__main__":
    main()
