#!/usr/bin/env python3
"""
NASDAQ-100 constituents fetcher.

Fetches the current NASDAQ-100 constituent list from Wikipedia
and writes it as JSON for use by the expansion pipeline.

Usage:
    python3 tools/fetch_nasdaq100_list.py
    python3 tools/fetch_nasdaq100_list.py --output nasdaq100.json
    python3 tools/fetch_nasdaq100_list.py --print
"""

import json
import re
import sys
import time
import argparse
import urllib.request
from pathlib import Path
from typing import List, Optional

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
USER_AGENT = "AssetIdentifiersRegistry/1.3.0 (contact: le.ptit.quantos@gmail.com)"
TIMEOUT = 30


def fetch_html(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def parse_tickers(html: str) -> List[str]:
    """Extract NASDAQ-100 ticker symbols from Wikipedia HTML."""
    tickers = []
    # Ticker symbols often appear as links to quote pages.
    pattern = re.compile(r'title="([A-Z][A-Z0-9.-]{0,9})"')
    matches = pattern.findall(html)

    # Wikipedia's Nasdaq-100 page contains many unrelated symbols.
    # Filter by known exchange context later, but for now collect and dedupe.
    seen = set()
    for ticker in matches:
        ticker = ticker.strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)
    return tickers


def main():
    parser = argparse.ArgumentParser(description="Fetch NASDAQ-100 constituents")
    parser.add_argument("--output", type=Path, default=Path("nasdaq100.json"))
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()

    html = fetch_html(WIKIPEDIA_URL)
    if not html:
        sys.exit(1)

    tickers = parse_tickers(html)
    # Filter out obvious non-ticker words.
    common_words = {
        "NASDAQ", "LIST", "HOLDINGS", "INC", "CORP", "COMPANY", "ETF",
        "INDEX", "STOCK", "SECURITIES", "TRUST", "FUND", "THE", "FOR",
        "AND", "WITH", "FROM", "THIS", "THAT", "WAS", "ARE", "NOT",
    }
    tickers = [t for t in tickers if t not in common_words and len(t) <= 5]

    print(f"Extracted {len(tickers)} potential NASDAQ-100 tickers")

    data = {
        "index": "NASDAQ-100",
        "source": "Wikipedia",
        "source_url": WIKIPEDIA_URL,
        "generated": time.strftime("%Y-%m-%d"),
        "count": len(tickers),
        "constituents": tickers,
    }

    if args.print:
        for t in tickers:
            print(t)
        sys.exit(0)

    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Written {len(tickers)} tickers to {args.output}")


if __name__ == "__main__":
    main()
