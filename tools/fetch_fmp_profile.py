#!/usr/bin/env python3
"""
FMP profile fetcher for Asset Identifier Registry expansion.

Fetches ISIN, CUSIP, CIK, exchange, sector, and metadata from
Financial Modeling Prep (FMP) stable/profile endpoint.

FMP gives both ISIN and CUSIP directly — no Yahoo derivation needed.

Usage:
    export FMP_API_KEY=your_key_here

    python3 tools/fetch_fmp_profile.py --limit 10 --dry-run
    python3 tools/fetch_fmp_profile.py --limit 50
    python3 tools/fetch_fmp_profile.py --tickers AAPL,MSFT,GOOGL --dry-run
    python3 tools/fetch_fmp_profile.py --sp500-file sp500.json

Notes:
    FMP free tier may have a daily request limit. The fetcher is
    resumable: if interrupted, re-run it. Tickers already added to
    identifiers.json with an ISIN are skipped on the next run.

Exit codes:
    0 — success
    1 — fetch/validation failure
    2 — usage error
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(2)

# ─── Constants ────────────────────────────────────────────────────────

FMP_BASE_URL = "https://financialmodelingprep.com"
FMP_PROFILE_URL = f"{FMP_BASE_URL}/stable/profile"

USER_AGENT = "AssetIdentifiersRegistry/1.3.0"

# Be polite. Adjust if your FMP plan allows faster access.
DEFAULT_DELAY_SECONDS = 0.6

# Map FMP exchange name to ISO 10383 MIC.
EXCHANGE_MAP = {
    "NASDAQ": "XNAS",
    "NYSE": "XNYS",
    "NYSE AMERICAN": "XNYS",
    "NYSE ARCA": "XNYS",
    "AMEX": "XNYS",
    "BATS": "BATS",
    "CBOE": "XCBO",
    "IEX": "IEXG",
}


# ─── API access ───────────────────────────────────────────────────────

def get_api_key() -> str:
    """Get FMP API key from environment."""
    key = os.environ.get("FMP_API_KEY", "").strip()
    if not key:
        print("ERROR: Set FMP_API_KEY environment variable", file=sys.stderr)
        print("  export FMP_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(2)
    return key


def fetch_profile(symbol: str, api_key: str) -> Optional[Dict]:
    """
    Fetch one FMP profile for a ticker.

    Returns the first profile dict, or None on any error.
    """
    url = f"{FMP_PROFILE_URL}?symbol={symbol}&apikey={api_key}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as e:
        print(f"  {symbol}: request error: {e}", file=sys.stderr)
        return None

    if response.status_code == 429:
        # Rate limited. Return a sentinel error by raising handled below.
        print(f"  {symbol}: HTTP 429 (rate limited)", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(f"  {symbol}: HTTP {response.status_code}", file=sys.stderr)
        return None

    try:
        data = response.json()
    except ValueError:
        print(f"  {symbol}: invalid JSON", file=sys.stderr)
        return None

    if not isinstance(data, list) or not data:
        print(f"  {symbol}: no profile returned", file=sys.stderr)
        return None

    return data[0]


# ─── Mapping helpers ──────────────────────────────────────────────────

def map_exchange_to_mic(fmp_exchange: str) -> Optional[str]:
    """Map FMP exchange string to a MIC."""
    if not fmp_exchange:
        return None
    return EXCHANGE_MAP.get(fmp_exchange.upper())


def map_asset_class(profile: Dict) -> str:
    """Return asset_class for FMP profile."""
    if profile.get("isEtf") or profile.get("isFund"):
        return "etf"
    return "equity"


# ─── Instrument builder ───────────────────────────────────────────────

def build_instrument(profile: Dict) -> Optional[Dict]:
    """Build a registry instrument dict from an FMP profile."""
    symbol = (profile.get("symbol") or "").upper().strip()
    name = (profile.get("companyName") or "").strip()
    exchange = profile.get("exchange") or ""
    mic = map_exchange_to_mic(exchange)

    if not symbol or not name:
        return None
    if not profile.get("isin"):
        return None
    if not mic:
        print(f"  {symbol}: unmapped exchange '{exchange}'", file=sys.stderr)
        return None

    instrument = {
        "isin": profile.get("isin"),
        "cusip": profile.get("cusip"),
        "sedol": None,
        "figi": None,          # OpenFIGI batch can fill later
        "lei": None,           # SEC/other source can fill later
        "ticker": symbol,
        "exchange": mic,
        "name": name,
        "currency": (profile.get("currency") or "USD").upper(),
        "asset_class": map_asset_class(profile),
        "instrument_type": "ETF" if map_asset_class(profile) == "etf" else "COMMON_STOCK",
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "country": (profile.get("country") or "US").upper(),
        "active": bool(profile.get("isActivelyTrading", True)),
        "listing_date": profile.get("ipoDate"),
        "delisting_date": None,
        "listings": [
            {
                "exchange": mic,
                "ticker": symbol,
                "currency": (profile.get("currency") or "USD").upper(),
                "status": "PRIMARY",
                "listing_date": profile.get("ipoDate"),
                "delisting_date": None,
            }
        ],
        "history": [
            {
                "ticker": symbol,
                "change_date": profile.get("ipoDate"),
                "change_type": "none",
                "reason": "INITIAL_LISTING",
                "source": "Financial Modeling Prep",
                "source_url": f"https://financialmodelingprep.com/stable/profile?symbol={symbol}",
            }
        ],
        "corporate_actions": [],
    }

    # Optional CIK — keep it even though FMP sometimes pads it.
    cik = profile.get("cik")
    if cik:
        instrument["cik"] = cik

    return instrument


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Expand Asset Identifier Registry using FMP stable/profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing identifiers.json")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process first N new tickers")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated explicit tickers to process")
    parser.add_argument("--data", type=Path, default=Path("identifiers.json"))
    parser.add_argument("--sp500-file", type=Path, default=Path("sp500.json"))
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS,
                        help=f"Delay between requests in seconds (default {DEFAULT_DELAY_SECONDS})")

    args = parser.parse_args()

    api_key = get_api_key()

    # Load registry.
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    existing_instruments = data.get("instruments", [])

    # Existing keys to avoid duplicates.
    existing_isins: Set[str] = {
        i["isin"].upper() for i in existing_instruments if i.get("isin")
    }
    existing_ticker_exchange: Set[Tuple[str, str]] = {
        (i.get("ticker", "").upper(), i.get("exchange", "").upper())
        for i in existing_instruments
        if i.get("ticker") and i.get("exchange")
    }

    # Determine target tickers.
    target_symbols: List[str] = []

    if args.tickers:
        target_symbols = [
            t.strip().upper()
            for t in args.tickers.split(",")
            if t.strip()
        ]
        print(f"Processing {len(target_symbols)} explicit ticker(s)")
    else:
        # Use S&P 500 constituents.
        try:
            with open(args.sp500_file, "r", encoding="utf-8") as f:
                sp500 = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: {args.sp500_file} not found. Run fetch_sp500_list.py first.", file=sys.stderr)
            sys.exit(2)

        constituents = sp500.get("constituents", [])
        sp500_symbols = [
            c.get("ticker", "").upper().strip()
            for c in constituents
            if c.get("ticker")
        ]

        # Filter to tickers that do not already have an ISIN on any mapped exchange.
        for sym in sp500_symbols:
            # We don't know FMP's exchange until fetch, so check only ISIN absence
            # by a cheap scan after fetching. Here, just take those not present
            # by (ticker, any known exchange) with ISIN.
            has_isin = any(
                i.get("ticker", "").upper() == sym and i.get("isin")
                for i in existing_instruments
            )
            if not has_isin:
                target_symbols.append(sym)

        print(f"S&P 500 candidates without ISIN: {len(target_symbols)}")

    # Deduplicate while preserving order.
    seen: Set[str] = set()
    unique_symbols: List[str] = []
    for sym in target_symbols:
        if sym not in seen:
            seen.add(sym)
            unique_symbols.append(sym)
    target_symbols = unique_symbols

    if args.limit:
        target_symbols = target_symbols[: args.limit]
        print(f"Limited to first {args.limit} ticker(s)")

    if not target_symbols:
        print("Nothing to process.")
        sys.exit(0)

    new_instruments: List[Dict] = []
    added = 0
    failed = 0

    print(f"\nFetching {len(target_symbols)} ticker(s) from FMP...\n")

    for idx, sym in enumerate(target_symbols, 1):
        profile = fetch_profile(sym, api_key)

        if profile is None:
            failed += 1
            # On rate-limit, be extra cautious.
            if idx % 25 == 0:
                print(f"  Processed {idx}/{len(target_symbols)} — sleeping 10s after possible rate limit...")
                time.sleep(10)
            else:
                time.sleep(args.delay)
            continue

        instrument = build_instrument(profile)

        if instrument is None:
            failed += 1
            time.sleep(args.delay)
            continue

        isin = instrument.get("isin", "").upper()
        key = (instrument.get("ticker", "").upper(), instrument.get("exchange", "").upper())

        # Skip if already present.
        if isin in existing_isins or key in existing_ticker_exchange:
            print(f"  {sym}: already in registry, skipping")
            time.sleep(args.delay)
            continue

        new_instruments.append(instrument)
        existing_isins.add(isin)
        existing_ticker_exchange.add(key)
        added += 1

        print(
            f"  {sym}: ISIN={instrument['isin']} "
            f"CUSIP={instrument.get('cusip')} "
            f"EXCH={instrument['exchange']}"
        )

        # Do not hammer the API.
        time.sleep(args.delay)

    print(f"\nNew instruments to add: {added}")
    print(f"Failed/skipped:          {failed}")

    if not new_instruments:
        print("No new instruments to merge.")
        sys.exit(0)

    if args.dry_run:
        preview_path = Path("identifiers.fmp.preview.json")
        preview = json.loads(json.dumps(data))
        preview["instruments"].extend(new_instruments)
        preview["meta"]["count"] = len(preview["instruments"])
        with open(preview_path, "w", encoding="utf-8") as f:
            json.dump(preview, f, indent=2, ensure_ascii=False)
        print(f"\nDry run — preview written to {preview_path}")
        sys.exit(0)

    # Merge into registry.
    data["instruments"].extend(new_instruments)

    # Refresh metadata.
    data["meta"]["count"] = len(data["instruments"])
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    sources = data["meta"].setdefault("sources", [])
    if "Financial Modeling Prep" not in sources:
        sources.append("Financial Modeling Prep")

    # Recompute coverage.
    exchanges = sorted({
        i.get("exchange") for i in data["instruments"] if i.get("exchange")
    })
    asset_classes = sorted({
        i.get("asset_class") for i in data["instruments"] if i.get("asset_class")
    })
    countries = sorted({
        i.get("country") for i in data["instruments"] if i.get("country")
    })
    coverage = data["meta"].setdefault("coverage", {})
    coverage["exchanges"] = exchanges
    coverage["asset_classes"] = asset_classes
    coverage["countries"] = countries

    with open(args.data, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nUpdated {args.data} with {added} new instrument(s).")
    print(f"Total instruments: {len(data['instruments'])}")


if __name__ == "__main__":
    main()
