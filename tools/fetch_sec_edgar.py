#!/usr/bin/env python3
"""
SEC EDGAR fetcher for Asset Identifier Registry.

Fetches company tickers, CIKs, and identifiers from SEC EDGAR
and updates identifiers.json with the results.

SEC EDGAR is the authoritative source for US-listed companies:
- Free, no API key required
- Updated daily
- Contains CIK, ticker, company name, exchange

Usage:
    python3 tools/fetch_sec_edgar.py --dry-run          # Preview changes
    python3 tools/fetch_sec_edgar.py                    # Apply changes
    python3 tools/fetch_sec_edgar.py --output new.json  # Write to file
    python3 tools/fetch_sec_edgar.py --limit 100        # Only process 100 companies

Exit codes:
    0 — success
    1 — validation failed
    2 — usage error
"""

import json
import sys
import time
import argparse
import gzip
import io
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ─── Constants ────────────────────────────────────────────────────────

SEC_EDGAR_COMPANY_TICKERS_URL = (
    "https://www.sec.gov/files/company_tickers.json"
)

SEC_EDGAR_SUBMISSIONS_URL = (
    "https://data.sec.gov/submissions/CIK{:010d}.json"
)

# SEC requires a User-Agent header
USER_AGENT = "AssetIdentifiersRegistry/1.0.0 (contact: le.ptit.quantos@gmail.com)"

# Rate limiting: SEC allows 10 requests per second
REQUEST_DELAY = 0.15  # ~6.7 requests per second (safe margin)

# Timeout for HTTP requests
TIMEOUT = 30

# Known exchange mappings from SEC to MIC codes
EXCHANGE_MAPPINGS = {
    "NASDAQ": "XNAS",
    "NYSE": "XNYS",
    "NYSE ARCA": "XNYS",
    "NYSE AMERICAN": "XNYS",
    "NYSE MKT": "XNYS",
    "OTC": None,  # Over-the-counter — not in our registry
    "OTCQX": None,
    "OTCQB": None,
    "PINK": None,
    "CBOE": "XCBO",
    "IEX": "IEXG",
    "BATS": "BATS",
    "BZX": "BATS",
}


# ─── Data Fetching ────────────────────────────────────────────────────

def fetch_json(url: str) -> Optional[Dict]:
    """
    Fetch JSON from a URL with proper User-Agent header.

    Handles gzip-compressed responses from SEC EDGAR.

    Args:
        url: URL to fetch

    Returns:
        Parsed JSON dict, or None on error
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()

            # Check if gzip-compressed
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)

            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  URL error for {url}: {e.reason}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  Invalid JSON from {url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


def fetch_company_tickers() -> Dict[str, Dict]:
    """
    Fetch all company tickers from SEC EDGAR.

    Returns:
        Dict mapping CIK string to company info dict:
        {
            "cik_str": "320193",
            "ticker": "AAPL",
            "title": "Apple Inc."
        }
    """
    print(f"Fetching SEC EDGAR company tickers...")
    data = fetch_json(SEC_EDGAR_COMPANY_TICKERS_URL)

    if not data:
        print("  Failed to fetch company tickers", file=sys.stderr)
        return {}

    print(f"  Received {len(data)} companies")
    return data


def fetch_company_submissions(cik: str) -> Optional[Dict]:
    """
    Fetch SEC submissions for a specific company by CIK.

    The submissions contain ISIN, exchange, and other identifiers
    in the company's latest filings.

    Args:
        cik: CIK as string (will be zero-padded to 10 digits)

    Returns:
        Submissions JSON dict, or None on error
    """
    cik_int = int(cik)
    url = SEC_EDGAR_SUBMISSIONS_URL.format(cik_int)
    return fetch_json(url)


def extract_isin_from_submissions(submissions: Dict) -> Optional[str]:
    """
    SEC EDGAR does NOT provide ISIN directly.

    This function is retained for API compatibility but always
    returns None. ISIN data must come from OpenFIGI or ANNA DSB.

    Args:
        submissions: SEC submissions JSON

    Returns:
        Always None — ISIN is not in SEC submissions
    """
    return None


def extract_cusip_from_submissions(submissions: Dict) -> Optional[str]:
    """
    Extract CUSIP from SEC submissions data.

    Args:
        submissions: SEC submissions JSON

    Returns:
        CUSIP string or None
    """
    if not submissions:
        return None

    issuer = submissions.get("issuer", {})
    cusip = issuer.get("cusip")
    if cusip:
        return cusip

    return None


def extract_lei_from_submissions(submissions: Dict) -> Optional[str]:
    """
    Extract LEI from SEC submissions data.

    Args:
        submissions: SEC submissions JSON

    Returns:
        LEI string or None
    """
    if not submissions:
        return None

    issuer = submissions.get("issuer", {})
    lei = issuer.get("lei")
    if lei:
        return lei

    return None


# ─── Data Processing ──────────────────────────────────────────────────

def map_exchange_to_mic(exchange_name: str) -> Optional[str]:
    """
    Map SEC exchange name to MIC code.

    Args:
        exchange_name: Exchange name from SEC (e.g., "NASDAQ", "NYSE")

    Returns:
        MIC code or None if not mapped
    """
    if not exchange_name:
        return None

    exchange_upper = exchange_name.upper().strip()

    for sec_name, mic in EXCHANGE_MAPPINGS.items():
        if sec_name in exchange_upper:
            return mic

    return None


def process_company(
    cik: str,
    company_info: Dict,
    existing_instruments: List[Dict],
) -> Optional[Dict]:
    """
    Process a single company from SEC EDGAR.

    Returns:
        Instrument dict ready for insertion, or None if skipped
    """
    ticker = company_info.get("ticker", "").upper()
    name = company_info.get("title", "")

    if not ticker or not name:
        return None

    # Use cik_str from company info (the JSON key may be unpadded)
    cik_str = company_info.get("cik_str", cik)
    
    # Fetch submissions for this company
    submissions = fetch_company_submissions(cik_str)
    time.sleep(REQUEST_DELAY)

    if not submissions:
        return None

    # SEC EDGAR provides: ticker, name, exchange, LEI, EIN
    # SEC EDGAR does NOT provide: ISIN, CUSIP, SEDOL, FIGI
    # Those come from OpenFIGI or ANNA DSB
    isin = None  # Not available from SEC
    cusip = None  # Not available from SEC
    lei = submissions.get("lei")  # May be None

    # ISIN is not available from SEC EDGAR directly.
    # We still return the instrument with the data we have.
    # ISIN will be filled in by fetch_identifiers.py (OpenFIGI) later.
    # For now, use ticker as a temporary identifier if no ISIN.

    # Extract exchange
    exchanges = submissions.get("exchanges", [])
    exchange_name = exchanges[0] if exchanges else ""
    mic = map_exchange_to_mic(exchange_name)

    if not mic:
        return None

    # Check if this ticker+exchange already exists
    for existing in existing_instruments:
        if (
            existing.get("ticker", "").upper() == ticker
            and existing.get("exchange") == mic
            and existing.get("isin")  # Only match instruments with ISIN
        ):
            # Update the existing instrument with fresh SEC data
            if lei:
                existing["lei"] = lei
            if name:
                existing["name"] = name
            
            # Update the source info in history
            if existing.get("history"):
                existing["history"][0]["source"] = "SEC EDGAR"
                existing["history"][0]["source_url"] = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik_str}"
                )
            
            return existing

    # New instrument — cannot add without ISIN
    # Will be handled by OpenFIGI enrichment pipeline
    return None


def merge_instruments(
    existing: List[Dict],
    new: List[Dict],
) -> Tuple[List[Dict], int, int]:
    """
    Merge new instruments into existing list.

    Returns:
        (merged_list, added_count, updated_count)
    """
    existing_by_isin = {i["isin"]: i for i in existing if i.get("isin")}

    added = 0
    updated = 0

    for instrument in new:
        isin = instrument.get("isin")
        if not isin:
            continue

        if isin in existing_by_isin:
            # Update existing instrument
            existing_by_isin[isin].update(instrument)
            updated += 1
        else:
            # Add new instrument
            existing.append(instrument)
            existing_by_isin[isin] = instrument
            added += 1

    return existing, added, updated


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and merge company identifiers from SEC EDGAR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying identifiers.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write result to a different file (implies --dry-run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N companies (for testing)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("identifiers.json"),
        help="Path to identifiers.json (default: identifiers.json)",
    )

    args = parser.parse_args()

    # Load existing registry
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {args.data}: {e}", file=sys.stderr)
        sys.exit(2)

    existing_instruments = data.get("instruments", [])

    # Fetch all companies from SEC EDGAR
    companies = fetch_company_tickers()

    if not companies:
        print("No companies fetched. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Sort by ticker for deterministic processing
    # Filter to companies with actual tickers first
    companies_with_tickers = {
        k: v for k, v in companies.items()
        if v.get("ticker") and v.get("ticker").strip()
    }
    sorted_companies = sorted(
        companies_with_tickers.items(),
        key=lambda x: x[1].get("ticker", "").upper(),
    )
    print(f"  Companies with tickers: {len(sorted_companies)}")

    # Filter to known tickers (existing instruments + common S&P 500 names)
    known_tickers = {i["ticker"].upper() for i in existing_instruments if i.get("ticker")}
    
    # Only match tickers already in our registry
    # This fetcher UPDATES existing instruments with fresh SEC data
    # New instruments require OpenFIGI enrichment first (ISIN/FIGI)
    target_tickers = known_tickers
    
    # Filter companies to target tickers
    filtered_companies = [
        (cik, info) for cik, info in sorted_companies
        if info.get("ticker", "").upper() in target_tickers
    ]
    
    print(f"  Target tickers: {len(target_tickers)}")
    print(f"  Matching companies: {len(filtered_companies)}")
    
    sorted_companies = filtered_companies
    
    # Apply limit if specified
    if args.limit:
        sorted_companies = sorted_companies[: args.limit]
        print(f"Limiting to {args.limit} companies")

    # Process companies
    new_instruments = []
    skipped = 0
    processed = 0

    for cik, company_info in sorted_companies:
        processed += 1

        if processed % 50 == 0:
            print(f"  Processed {processed}/{len(sorted_companies)}...")

        instrument = process_company(cik, company_info, existing_instruments)

        if instrument:
            new_instruments.append(instrument)
        else:
            skipped += 1

    print(f"\nProcessed: {processed}")
    print(f"Skipped:   {skipped}")
    print(f"Added/Updated: {len(new_instruments)}")

    # Merge
    merged, added, updated = merge_instruments(existing_instruments, new_instruments)
    print(f"Added:     {added}")
    print(f"Updated:   {updated}")

    # Update meta
    data["instruments"] = merged
    data["meta"]["count"] = len(merged)
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    if "SEC EDGAR" not in data["meta"]["sources"]:
        data["meta"]["sources"].append("SEC EDGAR")

    # Update coverage
    exchanges = set()
    asset_classes = set()
    countries = set()

    for instrument in merged:
        if instrument.get("exchange"):
            exchanges.add(instrument["exchange"])
        if instrument.get("asset_class"):
            asset_classes.add(instrument["asset_class"])
        if instrument.get("country"):
            countries.add(instrument["country"])

    data["meta"]["coverage"]["exchanges"] = sorted(exchanges)
    data["meta"]["coverage"]["asset_classes"] = sorted(asset_classes)
    data["meta"]["coverage"]["countries"] = sorted(countries)

    # Write result
    if args.dry_run or args.output:
        output_path = args.output or Path("identifiers.sec_edgar.preview.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nDry run complete. Result written to {output_path}")
        print("Run without --dry-run to apply changes to identifiers.json")
    else:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {args.data}")

    sys.exit(0)


if __name__ == "__main__":
    main()