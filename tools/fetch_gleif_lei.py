#!/usr/bin/env python3
"""
GLEIF LEI fetcher for Asset Identifier Registry.

Fetches Legal Entity Identifiers (LEIs) from the GLEIF API
using an instrument's ISIN.

Usage:
    python3 tools/fetch_gleif_lei.py --limit 10 --dry-run
    python3 tools/fetch_gleif_lei.py
"""

import json
import sys
import time
import argparse
from pathlib import Path
from typing import Optional

import requests

GLEIF_URL = "https://api.gleif.org/api/v1/lei-records"
DELAY = 0.4
TIMEOUT = 20
HEADERS = {"Accept": "application/vnd.api+json"}


def fetch_lei(isin: str) -> Optional[str]:
    """Fetch LEI from GLEIF for a given ISIN."""
    params = {
        "filter[isin]": isin,
        "page[size]": 1,
    }

    try:
        response = requests.get(GLEIF_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"  {isin}: request error: {e}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(f"  {isin}: HTTP {response.status_code}", file=sys.stderr)
        return None

    try:
        data = response.json()
    except ValueError:
        print(f"  {isin}: invalid JSON", file=sys.stderr)
        return None

    records = data.get("data", [])
    if not records:
        return None

    return records[0].get("attributes", {}).get("lei")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch LEI identifiers from GLEIF by ISIN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process first N instruments missing LEI")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing identifiers.json")
    parser.add_argument("--data", type=Path, default=Path("identifiers.json"))

    args = parser.parse_args()

    data = json.loads(args.data.read_text())
    instruments = data["instruments"]

    missing = [
        inst for inst in instruments
        if not inst.get("lei") and inst.get("isin")
    ]

    print(f"Instruments missing LEI: {len(missing)}")

    if args.limit:
        missing = missing[:args.limit]
        print(f"Limited to {len(missing)}")

    updated = 0
    failed = 0

    for idx, inst in enumerate(missing, 1):
        ticker = inst.get("ticker", "?")
        isin = inst.get("isin")

        lei = fetch_lei(isin)

        if lei:
            inst["lei"] = lei
            updated += 1
            print(f"  {ticker}: LEI={lei}")
        else:
            failed += 1
            print(f"  {ticker}: no LEI found")

        # Be polite to the GLEIF API.
        time.sleep(DELAY)

        if idx % 50 == 0:
            print(f"  Processed {idx}/{len(missing)}")

    print(f"\nUpdated: {updated}")
    print(f"Failed:  {failed}")

    if args.dry_run:
        preview_path = Path("identifiers.gleif.preview.json")
        preview_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\nPreview written to {preview_path}")
        sys.exit(0)

    # Write back.
    data["meta"]["count"] = len(data["instruments"])
    data["meta"]["data_valid_as_of"] = time.strftime("%Y-%m-%d")

    sources = data["meta"].setdefault("sources", [])
    if "GLEIF" not in sources:
        sources.append("GLEIF")

    args.data.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\nUpdated {args.data}")


if __name__ == "__main__":
    main()
