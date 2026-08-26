#!/usr/bin/env python3
"""
S&P 500 constituents fetcher.

Fetches the current S&P 500 constituent list from Wikipedia and
writes it to a JSON file for use by the expansion pipeline.

The S&P 500 is the most widely followed US equity index. Its
constituents are the top priority for registry expansion.

Source: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies

Usage:
    python3 tools/fetch_sp500_list.py                    # Fetch and write sp500.json
    python3 tools/fetch_sp500_list.py --output sp500.json  # Custom output path
    python3 tools/fetch_sp500_list.py --print            # Print to stdout only
    python3 tools/fetch_sp500_list.py --validate         # Validate against SEC EDGAR

Exit codes:
    0 — success
    1 — fetch failed
    2 — usage error
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ─── Constants ────────────────────────────────────────────────────────

WIKIPEDIA_SP500_URL = (
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
)

USER_AGENT = "AssetIdentifiersRegistry/1.0.0 (contact: le.ptit.quantos@gmail.com)"

TIMEOUT = 30

# Known S&P 500 tickers (fallback if Wikipedia fetch fails)
FALLBACK_SP500_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "NFLX",
    "JPM", "BAC", "GS", "V", "MA", "JNJ", "PFE", "UNH",
    "PG", "KO", "PEP", "WMT", "COST", "CAT", "BA", "GE",
    "HON", "XOM", "CVX", "DIS", "AMD", "TSLA", "INTC",
    "QCOM", "AVGO", "CSCO", "CRM", "PYPL", "SBUX", "BRK.B",
    "TMO", "ABT", "DHR", "LLY", "MRK", "ABBV", "BMY", "AMGN",
    "ADBE", "ORCL", "IBM", "ACN", "TXN", "MU", "ADI", "LRCX",
    "KLAC", "SNPS", "CDNS", "AMAT", "ASML", "INTU", "NOW", "PANW",
    "CRWD", "PLTR", "DDOG", "MDB", "ZS", "NET", "OKTA",
    "WFC", "C", "MS", "SCHW", "BLK", "BX", "KKR", "APO",
    "AXP", "COF", "DFS", "SYF", "USB", "PNC", "TFC",
    "HD", "LOW", "MCD", "SBUX", "YUM", "DHI", "LEN", "NVR",
    "TGT", "ROST", "TJX", "DG", "DLTR", "BBY", "ULTA",
    "MO", "PM", "CL", "KMB", "GIS", "K", "SYY", "ADM",
    "DUK", "SO", "D", "NEE", "AEP", "XEL", "WEC", "ES",
    "MMM", "ITW", "ETN", "PH", "ROK", "DOV", "CMI", "PCAR",
    "UPS", "FDX", "UNP", "CSX", "NSC", "ODFL", "LUV", "DAL",
    "UAL", "AAL", "RCL", "CCL", "NCLH", "EXPE", "BKNG", "MAR",
    "HLT", "H", "WYNN", "LVS", "MGM", "CZR",
    "LIN", "APD", "SHW", "ECL", "PPG", "IFF", "DD", "DOW",
    "NEM", "FCX", "NUE", "STLD", "VMC", "MLM", "PKG", "IP",
    "SLB", "HAL", "BKR", "OXY", "COP", "EOG", "PXD", "FANG",
    "DVN", "CTRA", "MRO", "APA", "HES",
    "PGR", "TRV", "ALL", "MET", "PRU", "AIG", "AFL", "CB",
    "PLD", "AMT", "EQIX", "SPG", "PSA", "O", "AVB", "EQR",
    "VTR", "WELL", "IRM", "DLR",
    "T", "VZ", "TMUS", "CMCSA", "CHTR", "DISH",
    "NKE", "LULU", "TPR", "RL", "PVH", "VFC",
    "EL", "CLX", "KVUE", "CHD", "COTY",
    "TSCO", "GWW", "FAST", "URI", "WSO", "AOS",
    "VRTX", "REGN", "BIIB", "GILD", "MRNA", "ALNY",
    "ISRG", "SYK", "BSX", "ZBH", "EW", "DXCM", "IDXX",
    "CI", "HUM", "CNC", "MOH", "ELV",
    "PLTR", "SNOW", "DDOG", "CRWD", "ZS", "NET", "OKTA", "MDB",
    "ENPH", "FSLR", "SEDG", "ALB", "CEG", "VST", "NRG",
    "WBD", "PARA", "FOXA", "FOX", "NWSA", "NWS",
    "WBA", "CVS", "MCK", "CAH", "COR",
    "ADP", "PAYX", "IR", "NDSN", "SWK", "SNA",
    "CTAS", "RSG", "WM", "GPN", "FIS", "FI", "JKHY",
]


# ─── Data Fetching ────────────────────────────────────────────────────

def fetch_wikipedia_html() -> Optional[str]:
    """
    Fetch the Wikipedia S&P 500 page HTML.

    Returns:
        HTML string or None on error
    """
    request = urllib.request.Request(
        WIKIPEDIA_SP500_URL,
        headers={"User-Agent": USER_AGENT},
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} fetching Wikipedia", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  URL error: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return None


def parse_wikipedia_tickers(html: str) -> List[Dict]:
    """
    Parse S&P 500 tickers from Wikipedia HTML.

    The first table on the page contains:
    - Ticker symbol (column 1)
    - Company name (column 2)
    - GICS sector (column 4)
    - GICS sub-industry (column 5)
    - Headquarters location (column 6)

    Args:
        html: Wikipedia page HTML

    Returns:
        List of dicts: [{"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", ...}]
    """
    companies = []
    in_table = False
    current_row = []

    for line in html.split("\n"):
        line = line.strip()

        # Detect table rows
        if "<tr" in line:
            in_table = True
            current_row = []
            continue

        if "</tr>" in line:
            if current_row:
                companies.append(parse_row(current_row))
            in_table = False
            continue

        if in_table:
            current_row.append(line)

    # Filter valid companies
    valid = []
    for company in companies:
        ticker = company.get("ticker", "").upper().strip()
        if ticker and len(ticker) <= 10 and not ticker.startswith("<"):
            valid.append(company)

    return valid


def parse_row(lines: List[str]) -> Dict:
    """
    Parse a single HTML table row into a company dict.

    Args:
        lines: List of HTML lines within a <tr> element

    Returns:
        Company dict
    """
    company = {"ticker": "", "name": "", "sector": "", "sub_industry": "", "headquarters": ""}

    cells = []
    current_cell = []

    for line in lines:
        if "<td" in line or "<th" in line:
            if current_cell:
                cells.append(" ".join(current_cell))
            current_cell = [line]
        elif "</td>" in line or "</th>" in line:
            current_cell.append(line)
            cells.append(" ".join(current_cell))
            current_cell = []
        else:
            current_cell.append(line)

    # Clean HTML tags from cells
    import re
    clean_cells = []
    for cell in cells:
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", cell).strip()
        # Remove Wikipedia references [1], [2], etc.
        clean = re.sub(r"\[\d+\]", "", clean).strip()
        # Remove extra whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        clean_cells.append(clean)

    # Extract fields from cells
    if len(clean_cells) >= 1:
        ticker_raw = clean_cells[0]
        # Extract ticker from links like "AAPL" or "NYSE: AAPL"
        ticker_match = re.search(r"([A-Z][A-Z0-9.-]{0,9})", ticker_raw)
        if ticker_match:
            company["ticker"] = ticker_match.group(1)

    if len(clean_cells) >= 2:
        company["name"] = clean_cells[1]

    if len(clean_cells) >= 4:
        company["sector"] = clean_cells[3]

    if len(clean_cells) >= 5:
        company["sub_industry"] = clean_cells[4]

    if len(clean_cells) >= 6:
        company["headquarters"] = clean_cells[5]

    return company


def use_fallback_tickers() -> List[Dict]:
    """
    Use the hardcoded fallback ticker list.

    Returns:
        List of dicts with just ticker (no metadata)
    """
    return [{"ticker": t, "name": "", "sector": "", "sub_industry": "", "headquarters": ""} for t in FALLBACK_SP500_TICKERS]


# ─── Validation ───────────────────────────────────────────────────────

def validate_against_sec(tickers: List[Dict]) -> Tuple[int, int]:
    """
    Validate tickers against SEC EDGAR.

    Args:
        tickers: List of company dicts with ticker field

    Returns:
        (matched, unmatched) counts
    """
    # Fetch SEC company tickers
    sec_url = "https://www.sec.gov/files/company_tickers.json"
    request = urllib.request.Request(
        sec_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            import gzip
            raw = response.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            sec_data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        print(f"  Failed to fetch SEC data: {e}", file=sys.stderr)
        return 0, len(tickers)

    # Build ticker set from SEC
    sec_tickers = set()
    for cik, info in sec_data.items():
        ticker = info.get("ticker", "").upper().strip()
        if ticker:
            sec_tickers.add(ticker)

    matched = 0
    unmatched = 0

    for company in tickers:
        ticker = company.get("ticker", "").upper().strip()
        if ticker in sec_tickers:
            matched += 1
        else:
            unmatched += 1

    return matched, unmatched


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch S&P 500 constituents from Wikipedia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sp500.json"),
        help="Output path (default: sp500.json)",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print to stdout only, don't write file",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate tickers against SEC EDGAR",
    )

    args = parser.parse_args()

    print("Fetching S&P 500 constituents from Wikipedia...")
    html = fetch_wikipedia_html()

    if html:
        companies = parse_wikipedia_tickers(html)
        print(f"  Parsed {len(companies)} companies from Wikipedia")
    else:
        print("  Wikipedia fetch failed. Using fallback list...")
        companies = use_fallback_tickers()
        print(f"  Fallback list has {len(companies)} tickers")

    if not companies:
        print("ERROR: No companies found", file=sys.stderr)
        sys.exit(1)

    # Deduplicate by ticker
    seen = set()
    unique_companies = []
    for company in companies:
        ticker = company.get("ticker", "").upper().strip()
        if ticker and ticker not in seen:
            seen.add(ticker)
            unique_companies.append(company)

    print(f"  Unique tickers: {len(unique_companies)}")

    # Validate against SEC if requested
    if args.validate:
        print("Validating against SEC EDGAR...")
        matched, unmatched = validate_against_sec(unique_companies)
        print(f"  Matched: {matched}")
        print(f"  Unmatched: {unmatched}")
        if unmatched > 0:
            print(f"  Match rate: {100 * matched // (matched + unmatched)}%")

    # Build output
    output_data = {
        "index": "S&P 500",
        "source": "Wikipedia",
        "source_url": WIKIPEDIA_SP500_URL,
        "generated": time.strftime("%Y-%m-%d"),
        "count": len(unique_companies),
        "constituents": unique_companies,
    }

    # Print mode
    if args.print:
        for company in unique_companies:
            print(company.get("ticker", "?"))
        sys.exit(0)

    # Write mode
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nWritten {len(unique_companies)} tickers to {args.output}")
    sys.exit(0)


if __name__ == "__main__":
    main()