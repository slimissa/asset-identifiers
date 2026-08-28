#!/usr/bin/env python3
"""
Massive (formerly Polygon.io) fetcher for Asset Identifier Registry.

Fetches CIK, FIGI, SIC code, market cap, description, and listing data
from the Massive REST API and enriches identifiers.json.

Massive provides:
- CIK (SEC Central Index Key) — permanent identifier
- Composite FIGI — permanent identifier
- Share class FIGI — permanent identifier
- SIC code and description — industry classification
- Market cap — company size
- List date — when the company went public
- Company description — business summary

Massive does NOT provide (free tier):
- CUSIP
- ISIN

Usage:
    python3 tools/fetch_massive.py --dry-run          # Preview changes
    python3 tools/fetch_massive.py                    # Apply changes
    python3 tools/fetch_massive.py --limit 10         # Test with 10 tickers
    python3 tools/fetch_massive.py --tickers AAPL,MSFT  # Specific tickers

Environment variables:
    MASSIVE_API_KEY    Required — API key from massive.com/dashboard/keys

Exit codes:
    0 — success
    1 — validation failed
    2 — usage error
"""

import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ─── Constants ────────────────────────────────────────────────────────

MASSIVE_API_BASE = "https://api.massive.com"
MASSIVE_TICKER_URL = f"{MASSIVE_API_BASE}/vX/reference/tickers/{{ticker}}?apiKey={{api_key}}"

# API key from environment
MASSIVE_API_KEY = os.environ.get("MASSIVE_API_KEY", "")

# Free tier: 5 calls per minute = 1 call per 12 seconds
REQUEST_DELAY = 12.5

TIMEOUT = 15

USER_AGENT = "AssetIdentifiersRegistry/1.0.0 (contact: le.ptit.quantos@gmail.com)"


# ─── Data Fetching ────────────────────────────────────────────────────

def fetch_ticker_details(ticker: str) -> Optional[Dict]:
    """
    Fetch ticker details from Massive REST API.

    Args:
        ticker: Ticker symbol (e.g., AAPL)

    Returns:
        Ticker details dict or None on error
    """
    if not MASSIVE_API_KEY:
        print("ERROR: MASSIVE_API_KEY environment variable not set", file=sys.stderr)
        return None

    url = MASSIVE_TICKER_URL.format(ticker=ticker, api_key=MASSIVE_API_KEY)

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK":
                return data.get("results", {})
            return None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  Rate limited for {ticker}. Waiting 60 seconds...", file=sys.stderr)
            time.sleep(60)
            return fetch_ticker_details(ticker)  # Retry once
        print(f"  HTTP {e.code} for {ticker}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  URL error for {ticker}: {e.reason}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  Invalid JSON for {ticker}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error for {ticker}: {e}", file=sys.stderr)
        return None


# ─── Instrument Enrichment ────────────────────────────────────────────

def enrich_instrument(instrument: Dict, details: Dict) -> Dict:
    """
    Enrich an instrument with Massive data.

    Args:
        instrument: Existing instrument dict
        details: Massive ticker details dict

    Returns:
        Enriched instrument dict
    """
    # CIK — SEC Central Index Key
    cik = details.get("cik")
    if cik:
        instrument["cik"] = cik

    # Composite FIGI
    composite_figi = details.get("composite_figi")
    if composite_figi and not instrument.get("figi"):
        instrument["figi"] = composite_figi

    # Share class FIGI
    share_class_figi = details.get("share_class_figi")
    if share_class_figi:
        instrument["share_class_figi"] = share_class_figi

    # SIC code and description
    sic_code = details.get("sic_code")
    if sic_code and not instrument.get("sic_code"):
        instrument["sic_code"] = sic_code

    sic_description = details.get("sic_description")
    if sic_description and not instrument.get("industry"):
        instrument["industry"] = sic_description

    # Market cap
    market_cap = details.get("market_cap")
    if market_cap:
        instrument["market_cap"] = market_cap

    # List date
    list_date = details.get("list_date")
    if list_date and not instrument.get("listing_date"):
        instrument["listing_date"] = list_date

    # Company description
    description = details.get("description")
    if description:
        instrument["description"] = description

    # Primary exchange
    primary_exchange = details.get("primary_exchange")
    if primary_exchange and not instrument.get("exchange"):
        instrument["exchange"] = primary_exchange

    # Active status
    active = details.get("active")
    if active is not None:
        instrument["active"] = active

    # Total employees
    total_employees = details.get("total_employees")
    if total_employees:
        instrument["total_employees"] = total_employees

    # Update history source
    if instrument.get("history"):
        instrument["history"][0]["source"] = "Massive (Polygon.io)"
        instrument["history"][0]["source_url"] = (
            f"https://massive.com/dashboard/keys?ticker={instrument.get('ticker', '')}"
        )

    return instrument


def process_ticker(
    ticker: str,
    existing_instruments: List[Dict],
) -> Optional[Dict]:
    """
    Process a single ticker: fetch from Massive and enrich.

    Args:
        ticker: Ticker symbol
        existing_instruments: All instruments in registry

    Returns:
        Enriched instrument dict or None
    """
    ticker = ticker.upper().strip()

    # Find existing instrument by ticker
    existing = None
    for inst in existing_instruments:
        if inst.get("ticker", "").upper() == ticker:
            existing = inst
            break

    if not existing:
        return None

    # Fetch details
    details = fetch_ticker_details(ticker)
    time.sleep(REQUEST_DELAY)

    if not details:
        return None

    # Enrich
    return enrich_instrument(existing, details)


def merge_instruments(
    existing: List[Dict],
    enriched: List[Dict],
) -> Tuple[List[Dict], int, int]:
    """
    Merge enriched instruments back into the registry.

    Returns:
        (merged, updated, failed)
    """
    existing_by_ticker = {
        i.get("ticker", "").upper(): i for i in existing if i.get("ticker")
    }

    updated = 0
    failed = 0

    for instrument in enriched:
        ticker = instrument.get("ticker", "").upper()
        if ticker in existing_by_ticker:
            existing_by_ticker[ticker] = instrument
            updated += 1
        else:
            failed += 1

    return list(existing_by_ticker.values()), updated, failed


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and enrich instruments with Massive (Polygon.io) data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated specific tickers")
    parser.add_argument("--data", type=Path, default=Path("identifiers.json"))

    args = parser.parse_args()

    # Check API key
    if not MASSIVE_API_KEY:
        print("ERROR: Set MASSIVE_API_KEY environment variable", file=sys.stderr)
        print("  export MASSIVE_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(2)

    # Load registry
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    existing_instruments = data.get("instruments", [])

    # Determine tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = [
            i.get("ticker", "").upper()
            for i in existing_instruments
            if i.get("ticker")
        ]

    if args.limit:
        tickers = tickers[: args.limit]
        print(f"Limiting to {args.limit} tickers")

    print(f"Processing {len(tickers)} tickers...")

    enriched = []
    succeeded = 0
    failed = 0

    for ticker in tickers:
        instrument = process_ticker(ticker, existing_instruments)
        if instrument:
            enriched.append(instrument)
            succeeded += 1
            figi = instrument.get("figi", "?")
            cik = instrument.get("cik", "?")
            print(f"  {ticker}: FIGI={figi} CIK={cik}")
        else:
            failed += 1
            print(f"  {ticker}: FAILED")

    print(f"\nSucceeded: {succeeded}")
    print(f"Failed:    {failed}")

    # Merge
    merged, updated, merge_failed = merge_instruments(existing_instruments, enriched)
    print(f"Updated:   {updated}")

    # Update meta
    data["instruments"] = merged
    data["meta"]["count"] = len(merged)
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    if "Massive (Polygon.io)" not in data["meta"]["sources"]:
        data["meta"]["sources"].append("Massive (Polygon.io)")

    # Update coverage
    figi_count = sum(1 for i in merged if i.get("figi"))
    cik_count = sum(1 for i in merged if i.get("cik"))
    sic_count = sum(1 for i in merged if i.get("sic_code"))
    print(f"\nFIGI coverage: {figi_count}/{len(merged)} ({100*figi_count//len(merged)}%)")
    print(f"CIK coverage:  {cik_count}/{len(merged)} ({100*cik_count//len(merged)}%)")
    print(f"SIC coverage:  {sic_count}/{len(merged)} ({100*sic_count//len(merged)}%)")

    # Write
    if args.dry_run:
        output_path = Path("identifiers.massive.preview.json")
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