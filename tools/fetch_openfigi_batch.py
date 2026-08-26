#!/usr/bin/env python3
"""
OpenFIGI Batch fetcher for Asset Identifier Registry.

Fetches FIGIs from OpenFIGI in batches of 100 for all instruments
in identifiers.json that have a ticker but no FIGI.

Usage:
    python3 tools/fetch_openfigi_batch.py --dry-run          # Preview changes
    python3 tools/fetch_openfigi_batch.py                    # Apply changes
    python3 tools/fetch_openfigi_batch.py --limit 50         # Process first 50
    python3 tools/fetch_openfigi_batch.py --tickers AAPL,MSFT,GOOGL

Environment variables:
    OPENFIGI_API_KEY    Optional API key for higher rate limits

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

OPENFIGI_MAPPING_URL = "https://api.openfigi.com/v3/mapping"

# Optional API key from environment
OPENFIGI_API_KEY = os.environ.get("OPENFIGI_API_KEY", "")

# Rate limits
# Without API key: 25 requests per second (but be conservative)
# With API key: 50 requests per second
REQUEST_DELAY = 0.5  # 2 batches per second (safe)

# Batch size (OpenFIGI max is 100)
BATCH_SIZE = 100

TIMEOUT = 30

USER_AGENT = "AssetIdentifiersRegistry/1.0.0 (contact: le.ptit.quantos@gmail.com)"


# ─── Data Fetching ────────────────────────────────────────────────────

def fetch_figi_batch(requests: List[Dict]) -> List[Optional[Dict]]:
    """
    Fetch FIGIs from OpenFIGI for a batch of tickers.

    Args:
        requests: List of request dicts:
            [{"idType": "TICKER", "idValue": "AAPL", "exchCode": "US"}]

    Returns:
        List of response dicts (same order as requests):
            [{"figi": "BBG000B9XRY4", "name": "APPLE INC", ...}]
            or None for failed lookups
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }

    if OPENFIGI_API_KEY:
        headers["X-OPENFIGI-APIKEY"] = OPENFIGI_API_KEY

    body = json.dumps(requests).encode("utf-8")

    request = urllib.request.Request(
        OPENFIGI_MAPPING_URL,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8")
            results = json.loads(raw)

            # Parse results — each element has "data" or "error"
            parsed = []
            for result in results:
                if "data" in result and result["data"]:
                    # Take the first match (most specific)
                    parsed.append(result["data"][0])
                else:
                    parsed.append(None)

            return parsed

    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} from OpenFIGI", file=sys.stderr)
        if e.code == 429:
            print("  Rate limited. Waiting 10 seconds...", file=sys.stderr)
            time.sleep(10)
        return [None] * len(requests)

    except urllib.error.URLError as e:
        print(f"  URL error: {e.reason}", file=sys.stderr)
        return [None] * len(requests)

    except json.JSONDecodeError as e:
        print(f"  Invalid JSON from OpenFIGI: {e}", file=sys.stderr)
        return [None] * len(requests)

    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return [None] * len(requests)


def map_exchange_to_openfigi(mic: str) -> str:
    """
    Map MIC code to OpenFIGI exchange code.

    Args:
        mic: MIC code (e.g., XNAS, XNYS)

    Returns:
        OpenFIGI exchange code (e.g., US, LN)
    """
    mapping = {
        "XNAS": "US",     # NASDAQ → US
        "XNYS": "US",     # NYSE → US
        "XLON": "LN",     # London → LN
        "XTKS": "JP",     # Tokyo → JP
        "XHKG": "HK",     # Hong Kong → HK
        "XETR": "GY",     # Deutsche Börse → GY
        "XPAR": "FP",     # Euronext Paris → FP
        "XSWX": "SW",     # SIX Swiss → SW
        "XKRX": "KS",     # Korea → KS
    }
    return mapping.get(mic, "US")  # Default to US


# ─── Main Processing ──────────────────────────────────────────────────

def build_batches(
    instruments: List[Dict],
    batch_size: int = BATCH_SIZE,
) -> List[List[Tuple[int, Dict]]]:
    """
    Build batches of OpenFIGI requests from instruments missing FIGI.

    Returns:
        List of batches, where each batch is a list of (index, instrument)
    """
    batches = []
    current_batch = []

    for idx, instrument in enumerate(instruments):
        ticker = instrument.get("ticker")
        exchange = instrument.get("exchange")
        figi = instrument.get("figi")

        # Skip instruments that already have FIGI
        if figi:
            continue

        # Skip instruments without ticker or exchange
        if not ticker or not exchange:
            continue

        exch_code = map_exchange_to_openfigi(exchange)

        current_batch.append((idx, {
            "idType": "TICKER",
            "idValue": ticker,
            "exchCode": exch_code,
        }))

        if len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []

    # Add remaining
    if current_batch:
        batches.append(current_batch)

    return batches


def process_instruments(
    data: Dict,
    limit: Optional[int] = None,
    specific_tickers: Optional[List[str]] = None,
) -> Tuple[int, int]:
    """
    Process all instruments missing FIGI.

    Returns:
        (filled_count, failed_count)
    """
    instruments = data.get("instruments", [])
    original_count = len(instruments)

    # Filter to specific tickers if requested
    if specific_tickers:
        specific_set = {t.upper() for t in specific_tickers}
        instruments = [i for i in instruments if i.get("ticker", "").upper() in specific_set]
        print(f"Filtered to {len(instruments)} specific instruments")

    # Apply limit
    if limit:
        instruments = instruments[:limit]
        print(f"Limited to {limit} instruments")

    # Build batches
    batches = build_batches(instruments)
    print(f"Batches to process: {len(batches)}")
    print(f"Instruments to query: {sum(len(b) for b in batches)}")

    filled = 0
    failed = 0

    for batch_idx, batch in enumerate(batches):
        # Prepare requests
        requests = [item[1] for item in batch]
        indices = [item[0] for item in batch]

        # Fetch batch
        results = fetch_figi_batch(requests)
        time.sleep(REQUEST_DELAY)

        # Update instruments
        for idx, result in zip(indices, results):
            instrument = instruments[idx] if idx < len(instruments) else None
            if not instrument:
                continue

            ticker = instrument.get("ticker", "?")

            if result:
                figi = result.get("figi")
                if figi:
                    instrument["figi"] = figi
                    # Also get name if missing
                    if not instrument.get("name") and result.get("name"):
                        instrument["name"] = result["name"]
                    filled += 1
                    if filled % 50 == 0:
                        print(f"  Filled {filled} FIGIs...")
                else:
                    failed += 1
            else:
                failed += 1

        if (batch_idx + 1) % 5 == 0:
            print(f"  Processed {batch_idx + 1}/{len(batches)} batches")

    print(f"\nFilled:  {filled}")
    print(f"Failed:  {failed}")
    print(f"Coverage: {filled}/{filled + failed} ({100 * filled // (filled + failed)}%)" if (filled + failed) > 0 else "")

    return filled, failed


def main():
    parser = argparse.ArgumentParser(
        description="Fetch FIGIs from OpenFIGI in batches",
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
        help="Only process first N instruments missing FIGI",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated specific tickers (e.g., AAPL,MSFT)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("identifiers.json"),
        help="Path to identifiers.json",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size (max {BATCH_SIZE})",
    )

    args = parser.parse_args()

    # Validate batch size
    if args.batch_size > BATCH_SIZE:
        print(f"Batch size {args.batch_size} exceeds max {BATCH_SIZE}", file=sys.stderr)
        sys.exit(2)

    # Load registry
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    # Parse specific tickers
    specific_tickers = None
    if args.tickers:
        specific_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    # Process
    original_figi_count = sum(1 for i in data["instruments"] if i.get("figi"))
    print(f"Starting FIGI coverage: {original_figi_count}/{len(data['instruments'])}")

    filled, failed = process_instruments(
        data,
        limit=args.limit,
        specific_tickers=specific_tickers,
    )

    new_figi_count = sum(1 for i in data["instruments"] if i.get("figi"))
    print(f"Ending FIGI coverage: {new_figi_count}/{len(data['instruments'])}")

    # Update meta
    data["meta"]["generated"] = time.strftime("%Y-%m-%d")
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    if "OpenFIGI" not in data["meta"]["sources"]:
        data["meta"]["sources"].append("OpenFIGI")

    # Write
    if args.dry_run:
        output_path = Path("identifiers.openfigi.preview.json")
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