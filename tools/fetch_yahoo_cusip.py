#!/usr/bin/env python3
"""
Yahoo Finance CUSIP fetcher for Asset Identifier Registry.

Fetches CUSIP identifiers from Yahoo Finance's unofficial API
and enriches identifiers.json with the results.

Yahoo Finance provides CUSIP for most US equities. This is the
missing piece needed to derive ISIN via Option C:
    ISIN = "US" + CUSIP + Luhn check digit

Usage:
    python3 tools/fetch_yahoo_cusip.py --dry-run          # Preview changes
    python3 tools/fetch_yahoo_cusip.py                    # Apply changes
    python3 tools/fetch_yahoo_cusip.py --limit 10         # Test with 10 tickers
    python3 tools/fetch_yahoo_cusip.py --tickers AAPL,MSFT,GOOGL  # Specific tickers

Exit codes:
    0 — success
    1 — validation failed
    2 — usage error
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ─── Constants ────────────────────────────────────────────────────────

YAHOO_QUOTE_SUMMARY_URL = (
    "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{}"
    "?modules=summaryProfile"
)

YAHOO_QUOTE_URL = (
    "https://query1.finance.yahoo.com/v7/finance/quote?symbols={}"
)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Rate limiting: Yahoo allows ~10 requests per second
REQUEST_DELAY = 0.25  # 4 requests per second (safe margin)

TIMEOUT = 15


# ─── Data Fetching ────────────────────────────────────────────────────

def fetch_json(url: str) -> Optional[Dict]:
    """
    Fetch JSON from Yahoo Finance API.

    Args:
        url: URL to fetch

    Returns:
        Parsed JSON dict, or None on error
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # Ticker not found on Yahoo
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


def fetch_cusip_from_summary(ticker: str) -> Optional[str]:
    """
    Fetch CUSIP from Yahoo Finance quoteSummary endpoint.

    Args:
        ticker: Ticker symbol (e.g., AAPL)

    Returns:
        CUSIP string (9 chars) or None
    """
    url = YAHOO_QUOTE_SUMMARY_URL.format(ticker)
    data = fetch_json(url)

    if not data:
        return None

    try:
        summary = data.get("quoteSummary", {})
        profile = summary.get("result", [{}])[0].get("summaryProfile", {})
        cusip = profile.get("cusip")
        if cusip and len(cusip) == 9:
            return cusip
    except (KeyError, IndexError, AttributeError):
        pass

    return None


def fetch_cusip_from_quote(ticker: str) -> Optional[str]:
    """
    Fetch CUSIP from Yahoo Finance quote endpoint (fallback).

    Args:
        ticker: Ticker symbol (e.g., AAPL)

    Returns:
        CUSIP string or None
    """
    url = YAHOO_QUOTE_URL.format(ticker)
    data = fetch_json(url)

    if not data:
        return None

    try:
        result = data.get("quoteResponse", {}).get("result", [])
        if result:
            quote = result[0]
            cusip = quote.get("cusip")
            if cusip and len(cusip) == 9:
                return cusip
    except (KeyError, IndexError, AttributeError):
        pass

    return None


def fetch_cusip(ticker: str) -> Optional[str]:
    """
    Fetch CUSIP from Yahoo Finance, trying both endpoints.

    Args:
        ticker: Ticker symbol

    Returns:
        CUSIP string or None
    """
    # Try quoteSummary first (more reliable)
    cusip = fetch_cusip_from_summary(ticker)
    if cusip:
        return cusip

    # Fallback to quote endpoint
    cusip = fetch_cusip_from_quote(ticker)
    if cusip:
        return cusip

    return None


# ─── ISIN Derivation ──────────────────────────────────────────────────

def derive_isin_from_cusip(cusip: str) -> Optional[str]:
    """
    Derive ISIN from CUSIP for US instruments.

    US ISIN format: "US" + CUSIP + Luhn check digit

    Args:
        cusip: 9-character CUSIP

    Returns:
        12-character ISIN or None if CUSIP is invalid
    """
    if not cusip or len(cusip) != 9:
        return None

    # Convert to uppercase
    cusip = cusip.upper()

    # Build ISIN body: "US" + CUSIP
    body = "US" + cusip

    # Compute Luhn check digit
    check_digit = compute_luhn_check_digit(body)

    return body + str(check_digit)


def compute_luhn_check_digit(body: str) -> int:
    """
    Compute Luhn check digit for an 11-character body.

    Args:
        body: 11-character alphanumeric string

    Returns:
        Check digit (0-9)
    """
    # Convert letters to numbers
    digits = []
    for char in body:
        if char.isalpha():
            num = ord(char.upper()) - ord('A') + 10
            digits.extend([num // 10, num % 10])
        elif char.isdigit():
            digits.append(int(char))
        else:
            return 0

    # Luhn algorithm: double every second digit from the right
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:
            doubled = digit * 2
            total += doubled // 10 + doubled % 10
        else:
            total += digit

    return (10 - (total % 10)) % 10


# ─── Main Processing ──────────────────────────────────────────────────

def process_ticker(
    ticker: str,
    existing_instruments: List[Dict],
) -> Optional[Dict]:
    """
    Process a single ticker: fetch CUSIP, derive ISIN, build instrument.

    Returns:
        Instrument dict or None
    """
    ticker = ticker.upper().strip()

    # Skip if already in registry
    for existing in existing_instruments:
        if existing.get("ticker", "").upper() == ticker:
            if existing.get("isin"):
                return existing  # Already has ISIN — nothing to do
            break

    # Fetch CUSIP
    cusip = fetch_cusip(ticker)
    time.sleep(REQUEST_DELAY)

    if not cusip:
        return None

    # Derive ISIN
    isin = derive_isin_from_cusip(cusip)
    if not isin:
        return None

    # Build instrument (FIGI will be filled by OpenFIGI later)
    return {
        "isin": isin,
        "cusip": cusip,
        "sedol": None,
        "figi": None,
        "lei": None,
        "ticker": ticker,
        "exchange": None,  # Unknown — SEC EDGAR will fill this
        "name": None,       # Unknown — SEC EDGAR will fill this
        "currency": "USD",
        "asset_class": "equity",
        "instrument_type": "COMMON_STOCK",
        "sector": None,
        "industry": None,
        "country": "US",
        "active": True,
        "listing_date": None,
        "delisting_date": None,
        "listings": [],
        "history": [
            {
                "ticker": ticker,
                "change_date": None,
                "change_type": "none",
                "reason": "INITIAL_LISTING",
                "source": "Yahoo Finance",
                "source_url": f"https://finance.yahoo.com/quote/{ticker}",
            }
        ],
        "corporate_actions": [],
    }


def merge_instruments(
    existing: List[Dict],
    new: List[Dict],
) -> Tuple[List[Dict], int, int]:
    """
    Merge new instruments into existing by ISIN.

    Returns:
        (merged, added, updated)
    """
    existing_by_isin = {i["isin"]: i for i in existing if i.get("isin")}

    added = 0
    updated = 0

    for instrument in new:
        isin = instrument.get("isin")
        if not isin:
            continue

        if isin in existing_by_isin:
            existing_by_isin[isin].update(instrument)
            updated += 1
        else:
            existing.append(instrument)
            existing_by_isin[isin] = instrument
            added += 1

    return existing, added, updated


def main():
    parser = argparse.ArgumentParser(
        description="Fetch CUSIP and derive ISIN from Yahoo Finance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying identifiers.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N tickers",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of specific tickers (e.g., AAPL,MSFT,GOOGL)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("identifiers.json"),
        help="Path to identifiers.json",
    )

    args = parser.parse_args()

    # Load existing registry
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    existing_instruments = data.get("instruments", [])

    # Determine tickers to process
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        # Use all tickers from existing instruments
        tickers = [
            i.get("ticker", "").upper()
            for i in existing_instruments
            if i.get("ticker")
        ]

    if args.limit:
        tickers = tickers[: args.limit]
        print(f"Limiting to {args.limit} tickers")

    print(f"Processing {len(tickers)} tickers...")

    new_instruments = []
    succeeded = 0
    failed = 0

    for ticker in tickers:
        instrument = process_ticker(ticker, existing_instruments)
        if instrument:
            new_instruments.append(instrument)
            succeeded += 1
            cusip = instrument.get("cusip", "?")
            isin = instrument.get("isin", "?")
            print(f"  {ticker}: CUSIP={cusip} ISIN={isin}")
        else:
            failed += 1
            print(f"  {ticker}: FAILED")

    print(f"\nSucceeded: {succeeded}")
    print(f"Failed:    {failed}")

    # Merge
    merged, added, updated = merge_instruments(existing_instruments, new_instruments)
    print(f"Added:     {added}")
    print(f"Updated:   {updated}")

    # Update meta
    data["instruments"] = merged
    data["meta"]["count"] = len(merged)
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    if "Yahoo Finance" not in data["meta"]["sources"]:
        data["meta"]["sources"].append("Yahoo Finance")

    # Write
    if args.dry_run:
        output_path = Path("identifiers.yahoo.preview.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nDry run complete. Preview written to {output_path}")
    else:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {args.data}")

    sys.exit(0)


if __name__ == "__main__":
    main()