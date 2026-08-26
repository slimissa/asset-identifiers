#!/usr/bin/env python3
"""
SEC EDGAR fetcher for Asset Identifier Registry.

Fetches company tickers, names, exchanges, and LEIs from SEC EDGAR
and updates identifiers.json with the results.

SEC EDGAR is the authoritative source for US-listed companies:
- Free, no API key required
- Updated daily
- Contains CIK, ticker, company name, exchange

Usage:
    python3 tools/fetch_sec_edgar.py --dry-run          # Preview changes
    python3 tools/fetch_sec_edgar.py                    # Apply changes
    python3 tools/fetch_sec_edgar.py --limit 100        # Only process 100 companies
    python3 tools/fetch_sec_edgar.py --sp500            # Process all S&P 500 tickers
    python3 tools/fetch_sec_edgar.py --tickers AAPL,MSFT  # Specific tickers

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

USER_AGENT = "AssetIdentifiersRegistry/1.0.0 (contact: le.ptit.quantos@gmail.com)"

REQUEST_DELAY = 0.15
TIMEOUT = 30

EXCHANGE_MAPPINGS = {
    "NASDAQ": "XNAS",
    "NYSE": "XNYS",
    "NYSE ARCA": "XNYS",
    "NYSE AMERICAN": "XNYS",
    "NYSE MKT": "XNYS",
    "OTC": None,
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
    """Fetch JSON from URL with gzip support."""
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
    """Fetch all company tickers from SEC EDGAR."""
    print("Fetching SEC EDGAR company tickers...")
    data = fetch_json(SEC_EDGAR_COMPANY_TICKERS_URL)

    if not data:
        print("  Failed to fetch company tickers", file=sys.stderr)
        return {}

    print(f"  Received {len(data)} companies")
    return data


def fetch_company_submissions(cik: str) -> Optional[Dict]:
    """Fetch SEC submissions for a company by CIK."""
    cik_int = int(cik)
    url = SEC_EDGAR_SUBMISSIONS_URL.format(cik_int)
    return fetch_json(url)


def map_exchange_to_mic(exchange_name: str) -> Optional[str]:
    """Map SEC exchange name to MIC code."""
    if not exchange_name:
        return None

    exchange_upper = exchange_name.upper().strip()

    for sec_name, mic in EXCHANGE_MAPPINGS.items():
        if sec_name in exchange_upper:
            return mic

    return None


# ─── Instrument Building ──────────────────────────────────────────────

def build_new_instrument(
    ticker: str,
    name: str,
    mic: str,
    lei: Optional[str],
    cik_str: str,
) -> Dict:
    """
    Build a complete instrument entry from SEC EDGAR data.

    This is the ONLY place new instruments are created from SEC data.
    ISIN and CUSIP will be filled by Yahoo Finance fetcher later.
    FIGI will be filled by OpenFIGI fetcher later.
    """
    return {
        "isin": None,  # Filled by fetch_yahoo_cusip.py
        "cusip": None,  # Filled by fetch_yahoo_cusip.py
        "sedol": None,
        "figi": None,  # Filled by fetch_openfigi_batch.py
        "lei": lei,
        "ticker": ticker,
        "exchange": mic,
        "name": name,
        "currency": "USD",
        "asset_class": "equity",
        "instrument_type": "COMMON_STOCK",
        "sector": None,
        "industry": None,
        "country": "US",
        "active": True,
        "listing_date": None,
        "delisting_date": None,
        "listings": [
            {
                "exchange": mic,
                "ticker": ticker,
                "currency": "USD",
                "status": "PRIMARY",
                "listing_date": None,
                "delisting_date": None,
            }
        ],
        "history": [
            {
                "ticker": ticker,
                "change_date": None,
                "change_type": "none",
                "reason": "INITIAL_LISTING",
                "source": "SEC EDGAR",
                "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik_str}",
            }
        ],
        "corporate_actions": [],
    }


def process_company(
    cik: str,
    company_info: Dict,
    existing_instruments: List[Dict],
) -> Optional[Dict]:
    """
    Process a single company from SEC EDGAR.

    Returns updated existing instrument, new instrument, or None.
    """
    ticker = company_info.get("ticker", "").upper().strip()
    name = company_info.get("title", "").strip()

    if not ticker or not name:
        return None

    cik_str = company_info.get("cik_str", cik)

    submissions = fetch_company_submissions(cik_str)
    time.sleep(REQUEST_DELAY)

    if not submissions:
        return None

    lei = submissions.get("lei")

    exchanges = submissions.get("exchanges", [])
    exchange_name = exchanges[0] if exchanges else ""
    mic = map_exchange_to_mic(exchange_name)

    if not mic:
        return None

    # Check if this ticker+exchange already exists with ISIN
    for existing in existing_instruments:
        if (
            existing.get("ticker", "").upper() == ticker
            and existing.get("exchange") == mic
            and existing.get("isin")
        ):
            # Update existing instrument
            if lei:
                existing["lei"] = lei
            if name:
                existing["name"] = name
            if existing.get("history"):
                existing["history"][0]["source"] = "SEC EDGAR"
                existing["history"][0]["source_url"] = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik_str}"
                )
            return existing

    # New instrument — build without ISIN (filled by Yahoo fetcher later)
    return build_new_instrument(ticker, name, mic, lei, cik_str)


def merge_instruments(
    existing: List[Dict],
    new: List[Dict],
) -> Tuple[List[Dict], int, int]:
    """
    Merge new instruments into existing by ISIN or ticker+exchange.

    Returns:
        (merged, added, updated)
    """
    existing_by_isin = {i["isin"]: i for i in existing if i.get("isin")}
    existing_by_ticker_exchange = {
        (i.get("ticker", "").upper(), i.get("exchange")): i
        for i in existing
        if i.get("ticker") and i.get("exchange")
    }

    added = 0
    updated = 0

    for instrument in new:
        isin = instrument.get("isin")
        ticker = instrument.get("ticker", "").upper()
        exchange = instrument.get("exchange")

        # Try ISIN match first
        if isin and isin in existing_by_isin:
            existing_by_isin[isin].update(instrument)
            updated += 1
            continue

        # Try ticker+exchange match
        key = (ticker, exchange)
        if key in existing_by_ticker_exchange:
            existing_by_ticker_exchange[key].update(instrument)
            updated += 1
            continue

        # New instrument
        existing.append(instrument)
        added += 1

        # Update lookup dicts
        if isin:
            existing_by_isin[isin] = instrument
        existing_by_ticker_exchange[key] = instrument

    return existing, added, updated


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and merge company data from SEC EDGAR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated specific tickers")
    parser.add_argument("--sp500", action="store_true",
                        help="Process all S&P 500 tickers from sp500.json")
    parser.add_argument("--data", type=Path, default=Path("identifiers.json"))
    parser.add_argument("--sp500-file", type=Path, default=Path("sp500.json"))

    args = parser.parse_args()

    # Load existing registry
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    existing_instruments = data.get("instruments", [])

    # Build target ticker set
    target_tickers: Set[str] = set()

    if args.tickers:
        target_tickers = {t.strip().upper() for t in args.tickers.split(",") if t.strip()}
    elif args.sp500:
        try:
            with open(args.sp500_file, "r", encoding="utf-8") as f:
                sp500_data = json.load(f)
            target_tickers = {
                c.get("ticker", "").upper().strip()
                for c in sp500_data.get("constituents", [])
                if c.get("ticker")
            }
            print(f"Loaded {len(target_tickers)} tickers from {args.sp500_file}")
        except FileNotFoundError:
            print(f"ERROR: {args.sp500_file} not found. Run fetch_sp500_list.py first.", file=sys.stderr)
            sys.exit(2)
    else:
        # Default: existing registry tickers
        target_tickers = {
            i.get("ticker", "").upper()
            for i in existing_instruments
            if i.get("ticker")
        }
        print(f"Using {len(target_tickers)} existing registry tickers")

    # Fetch all companies
    companies = fetch_company_tickers()
    if not companies:
        print("No companies fetched. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Filter to target tickers
    companies_with_tickers = {
        k: v for k, v in companies.items()
        if v.get("ticker") and v.get("ticker").strip().upper() in target_tickers
    }

    sorted_companies = sorted(
        companies_with_tickers.items(),
        key=lambda x: x[1].get("ticker", "").upper(),
    )

    print(f"  Matching companies: {len(sorted_companies)}")

    if args.limit:
        sorted_companies = sorted_companies[: args.limit]
        print(f"  Limiting to {args.limit}")

    # Process
    new_instruments = []
    processed = 0

    for cik, company_info in sorted_companies:
        processed += 1
        if processed % 50 == 0:
            print(f"  Processed {processed}/{len(sorted_companies)}...")

        instrument = process_company(cik, company_info, existing_instruments)
        if instrument:
            new_instruments.append(instrument)

    # Merge
    merged, added, updated = merge_instruments(existing_instruments, new_instruments)
    print(f"\nProcessed: {processed}")
    print(f"Added:     {added}")
    print(f"Updated:   {updated}")
    print(f"Total:     {len(merged)}")

    # Update meta
    data["instruments"] = merged
    data["meta"]["count"] = len(merged)
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")
    if "SEC EDGAR" not in data["meta"]["sources"]:
        data["meta"]["sources"].append("SEC EDGAR")

    # Update coverage
    exchanges = {i["exchange"] for i in merged if i.get("exchange")}
    asset_classes = {i["asset_class"] for i in merged if i.get("asset_class")}
    countries = {i["country"] for i in merged if i.get("country")}
    data["meta"]["coverage"]["exchanges"] = sorted(exchanges)
    data["meta"]["coverage"]["asset_classes"] = sorted(asset_classes)
    data["meta"]["coverage"]["countries"] = sorted(countries)

    # Write
    if args.dry_run:
        output_path = Path("identifiers.sec_edgar.preview.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nPreview written to {output_path}")
    else:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {args.data}")

    sys.exit(0)


if __name__ == "__main__":
    main()