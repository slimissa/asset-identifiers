#!/usr/bin/env python3
"""
FMP profile fetcher for Asset Identifier Registry expansion.

Fetches ISIN, CUSIP, CIK, exchange, sector, and metadata from
Financial Modeling Prep (FMP) stable/profile endpoint.

FMP gives both ISIN and CUSIP directly — no Yahoo derivation needed.

Merge behavior:
    When a matching instrument already exists (by ticker+exchange) but
    has no ISIN, FMP data is merged into that record. This is the normal
    case after running fetch_sec_edgar.py, which creates skeletons with
    isin=None that FMP later fills.

    When the matching instrument already has an ISIN, it is skipped.

Usage:
    export FMP_API_KEY=your_key_here

    python3 tools/fetch_fmp_profile.py --limit 10 --dry-run
    python3 tools/fetch_fmp_profile.py --limit 50
    python3 tools/fetch_fmp_profile.py --tickers AAPL,MSFT,GOOGL --dry-run
    python3 tools/fetch_fmp_profile.py --sp500-file sp500.json

Notes:
    FMP free tier may have a daily request limit. The fetcher is
    resumable: run it, wait for the daily limit to reset, run again.
    Tickers that already have an ISIN are skipped on subsequent runs.

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

USER_AGENT = "AssetIdentifiersRegistry/1.5.0"

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


# ─── Guard: refuse to write outside LAS_DATA_HOME ─────────────────────

def check_data_home(data_path: Path) -> None:
    """
    Refuse to write identifier data outside $LAS_DATA_HOME.

    This guard prevents accidentally writing licensed data into a public
    git repository. It is a no-op if LAS_DATA_HOME is unset (bootstrap).
    """
    las_home = os.environ.get("LAS_DATA_HOME", "").strip()
    if not las_home:
        return

    las_home_path = Path(las_home).resolve()
    data_path_resolved = data_path.resolve()

    try:
        data_path_resolved.relative_to(las_home_path)
    except ValueError:
        print(
            f"ERROR: --data {data_path_resolved} is outside $LAS_DATA_HOME "
            f"({las_home_path})",
            file=sys.stderr,
        )
        print(
            "  This guard prevents accidentally writing identifier data "
            "into a public repository.",
            file=sys.stderr,
        )
        print(
            "  Unset LAS_DATA_HOME, or move --data under the private store.",
            file=sys.stderr,
        )
        sys.exit(2)


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
        print(f"  {symbol}: HTTP 429 (rate limited)", file=sys.stderr)
        return None

    if response.status_code == 402:
        # FMP 402 = payment required / symbol not covered by plan.
        print(f"  {symbol}: HTTP 402 (not covered by plan)", file=sys.stderr)
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

    currency = (profile.get("currency") or "USD").upper()
    ipo_date = profile.get("ipoDate")
    asset_class = map_asset_class(profile)

    instrument = {
        "isin": profile.get("isin"),
        "cusip": profile.get("cusip"),
        "sedol": None,
        "figi": None,          # OpenFIGI batch fills this later
        "lei": None,           # SEC/GLEIF fills this later
        "ticker": symbol,
        "exchange": mic,
        "name": name,
        "currency": currency,
        "asset_class": asset_class,
        "instrument_type": "ETF" if asset_class == "etf" else "COMMON_STOCK",
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "country": (profile.get("country") or "US").upper(),
        "active": bool(profile.get("isActivelyTrading", True)),
        "listing_date": ipo_date,
        "delisting_date": None,
        "listings": [
            {
                "exchange": mic,
                "ticker": symbol,
                "currency": currency,
                "status": "PRIMARY",
                "listing_date": ipo_date,
                "delisting_date": None,
            }
        ],
        "history": [
            {
                "ticker": symbol,
                "change_date": ipo_date,
                "change_type": "none",
                "reason": "INITIAL_LISTING",
                "source": "Financial Modeling Prep",
                "source_url": f"https://financialmodelingprep.com/stable/profile?symbol={symbol}",
            }
        ],
        "corporate_actions": [],
    }

    cik = profile.get("cik")
    if cik:
        instrument["cik"] = cik

    return instrument


# ─── Merge logic ──────────────────────────────────────────────────────

# Fields FMP provides that should overwrite a None on an existing record.
# Existing non-None values are preserved.
MERGE_FIELDS = (
    "isin",
    "cusip",
    "name",
    "currency",
    "asset_class",
    "instrument_type",
    "sector",
    "industry",
    "country",
    "active",
    "listing_date",
    "cik",
)


def merge_into_existing(existing: Dict, new: Dict) -> None:
    """
    Merge FMP data into an existing record in place.

    Only fills fields that are currently None on the existing record.
    Preserves SEC-derived fields like lei, history source, and any
    identifier already populated by a previous fetcher.
    """
    for field in MERGE_FIELDS:
        new_val = new.get(field)
        if new_val is not None and existing.get(field) is None:
            existing[field] = new_val

    # If we just backfilled listing_date above, the existing record's
    # initial history entry (created by fetch_sec_edgar.py before a
    # listing date was known) is likely still carrying a null
    # change_date. Sync it now so the two don't permanently desync —
    # this null/populated mismatch is what produced 464 schema-invalid
    # records in the live dataset.
    existing_history = existing.get("history")
    new_history = new.get("history")
    if existing_history and existing_history[0].get("change_date") is None:
        if new_history and new_history[0].get("change_date") is not None:
            existing_history[0]["change_date"] = new_history[0]["change_date"]

    # If the existing record has no listings, adopt the FMP listings.
    if not existing.get("listings") and new.get("listings"):
        existing["listings"] = new["listings"]

    # If the existing record has no history, adopt the FMP history.
    if not existing.get("history") and new.get("history"):
        existing["history"] = new["history"]


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Enrich Asset Identifier Registry using FMP stable/profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing identifiers.json")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process first N candidate tickers")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated explicit tickers to process")
    parser.add_argument("--tickers-file", type=Path, default=None,
                        help="Path to JSON file with a 'tickers' list")
    parser.add_argument("--data", type=Path, default=Path("identifiers.json"),
                        help="Path to identifiers.json")
    parser.add_argument("--sp500-file", type=Path, default=Path("sp500.json"),
                        help="Path to sp500.json (constituents list)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS,
                        help=f"Delay between requests in seconds (default {DEFAULT_DELAY_SECONDS})")

    args = parser.parse_args()

    check_data_home(args.data)

    api_key = get_api_key()

    # Load registry.
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    existing_instruments = data.get("instruments", [])

    # Build index: (ticker_upper, exchange_upper) -> existing record.
    # This lets us check the presence of an ISIN on a per-record basis.
    existing_by_pair: Dict[Tuple[str, str], Dict] = {}
    for inst in existing_instruments:
        t = inst.get("ticker", "").upper()
        e = inst.get("exchange", "").upper()
        if t and e:
            existing_by_pair[(t, e)] = inst

    # Determine target symbols.
    target_symbols: List[str] = []

    if args.tickers:
        target_symbols = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        print(f"Processing {len(target_symbols)} explicit ticker(s)")
    elif args.tickers_file:
        with open(args.tickers_file, "r", encoding="utf-8") as f:
            ticker_data = json.load(f)
        target_symbols = [str(t).upper() for t in ticker_data.get("tickers", [])]
        print(f"Processing {len(target_symbols)} ticker(s) from {args.tickers_file}")
    else:
        try:
            with open(args.sp500_file, "r", encoding="utf-8") as f:
                sp500 = json.load(f)
        except FileNotFoundError:
            print(
                f"ERROR: {args.sp500_file} not found. Run fetch_sp500_list.py first.",
                file=sys.stderr,
            )
            sys.exit(2)

        constituents = sp500.get("constituents", [])
        sp500_symbols = [
            c.get("ticker", "").upper().strip()
            for c in constituents
            if c.get("ticker")
        ]

        for sym in sp500_symbols:
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

    added = 0
    merged = 0
    skipped_has_isin = 0
    failed = 0

    print(f"\nFetching {len(target_symbols)} ticker(s) from FMP...\n")

    for idx, sym in enumerate(target_symbols, 1):
        profile = fetch_profile(sym, api_key)

        if profile is None:
            failed += 1
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

        key = (
            instrument.get("ticker", "").upper(),
            instrument.get("exchange", "").upper(),
        )

        existing = existing_by_pair.get(key)

        if existing is not None and existing.get("isin"):
            print(f"  {sym}: already has ISIN, skipping")
            skipped_has_isin += 1
            time.sleep(args.delay)
            continue

        if existing is not None:
            merge_into_existing(existing, instrument)
            merged += 1
            print(
                f"  {sym}: merged ISIN={instrument['isin']} "
                f"CUSIP={instrument.get('cusip')} EXCH={instrument['exchange']}"
            )
        else:
            existing_instruments.append(instrument)
            existing_by_pair[key] = instrument
            added += 1
            print(
                f"  {sym}: added ISIN={instrument['isin']} "
                f"CUSIP={instrument.get('cusip')} EXCH={instrument['exchange']}"
            )

        time.sleep(args.delay)

    print(f"\nAdded:              {added}")
    print(f"Merged into existing: {merged}")
    print(f"Skipped (has ISIN):  {skipped_has_isin}")
    print(f"Failed:              {failed}")

    if added == 0 and merged == 0:
        print("No changes to write.")
        sys.exit(0)

    # Refresh metadata.
    data["instruments"] = existing_instruments
    data["meta"]["count"] = len(existing_instruments)
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    sources = data["meta"].setdefault("sources", [])
    if "Financial Modeling Prep" not in sources:
        sources.append("Financial Modeling Prep")

    # Refresh coverage.
    exchanges = sorted({i.get("exchange") for i in existing_instruments if i.get("exchange")})
    asset_classes = sorted({i.get("asset_class") for i in existing_instruments if i.get("asset_class")})
    countries = sorted({i.get("country") for i in existing_instruments if i.get("country")})
    coverage = data["meta"].setdefault("coverage", {})
    coverage["exchanges"] = exchanges
    coverage["asset_classes"] = asset_classes
    coverage["countries"] = countries

    # Write.
    if args.dry_run:
        preview_path = args.data.with_suffix(".fmp.preview.json")
        with open(preview_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nDry run — preview written to {preview_path}")
        sys.exit(0)

    with open(args.data, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    isin_count = sum(1 for i in existing_instruments if i.get("isin"))
    print(f"\nUpdated {args.data}")
    print(f"Total instruments: {len(existing_instruments)}")
    print(f"ISIN coverage: {isin_count}/{len(existing_instruments)} "
          f"({100 * isin_count // len(existing_instruments)}%)")


if __name__ == "__main__":
    main()