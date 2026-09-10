#!/usr/bin/env python3
"""Generate a synthetic test fixture for the asset-identifiers registry.

All identifiers are fake but pass check-digit validation. Used only for tests.
No real instrument data, no data from FMP, OpenFIGI, Yahoo, or any vendor.
"""

import json
from pathlib import Path


# ─── Check-digit helpers ──────────────────────────────────────────────

def cusip_check(base8: str) -> str:
    """Compute the CUSIP check digit for an 8-character base.

    Positions 1..8 (1-indexed). Even positions (2, 4, 6, 8) are doubled.
    """
    assert len(base8) == 8, "base must be 8 chars"
    total = 0
    for i, ch in enumerate(base8):          # i = 0..7, position = i+1
        if ch.isdigit():
            v = int(ch)
        else:
            v = ord(ch.upper()) - ord('A') + 10
        if (i + 1) % 2 == 0:                # even position -> double
            v *= 2
        total += v // 10 + v % 10
    return str((10 - (total % 10)) % 10)


def isin_check(first11: str) -> str:
    """Compute the ISIN check digit for an 11-character prefix.

    Iterate the numeric payload from RIGHT to LEFT, doubling ODD positions
    (1st, 3rd, 5th, ... from the right of the payload). Equivalent to the
    standard Luhn algorithm where the check digit occupies position 1 of
    the full 12-char string and is not doubled.
    """
    assert len(first11) == 11, "first11 must be 11 chars"
    digits = ''.join(
        ch if ch.isdigit() else str(ord(ch.upper()) - ord('A') + 10)
        for ch in first11
    )
    total = 0
    for i, ch in enumerate(reversed(digits)):   # i = 0 is rightmost
        v = int(ch)
        if i % 2 == 0:                          # odd position from right -> double
            v *= 2
        total += v // 10 + v % 10
    return str((10 - (total % 10)) % 10)


# ─── Instrument builder ───────────────────────────────────────────────

def make_instrument(
    ticker,
    country,
    cusip_base,
    name,
    exchange,
    currency,
    asset_class="equity",
    figi="BBG000000001",
    lei="00000000000000000001",
    listings=None,
    history=None,
    active=True,
    listing_date="2000-01-01",
):
    cusip = cusip_base + cusip_check(cusip_base)
    isin = country + cusip + isin_check(country + cusip)

    if listings is None:
        listings = [{
            "exchange": exchange,
            "ticker": ticker,
            "currency": currency,
            "status": "PRIMARY",
        }]

    if history is None:
        history = [{
            "ticker": ticker,
            "change_date": listing_date,
            "change_type": "none",
            "source": "synthetic",
            "source_url": "https://example.invalid/synthetic",
        }]

    return {
        "isin": isin,
        "cusip": cusip if country in ("US", "CA") else None,
        "sedol": None,
        "figi": figi,
        "lei": lei,
        "ticker": ticker,
        "exchange": exchange,
        "name": name,
        "currency": currency,
        "asset_class": asset_class,
        "country": country,
        "active": active,
        "listings": listings,
        "history": history,
    }


# ─── Instrument set ───────────────────────────────────────────────────

instruments = [
    make_instrument(
        ticker="TESTA", country="US", cusip_base="00000000",
        name="Synthetic Test A", exchange="XNAS", currency="USD",
        figi="BBG000000001", lei="00000000000000000001",
    ),
    make_instrument(
        ticker="TESTB", country="US", cusip_base="00000001",
        name="Synthetic Test B", exchange="XNAS", currency="USD",
        figi="BBG000000002", lei="00000000000000000002",
    ),
    make_instrument(
        ticker="NEWTICK", country="US", cusip_base="00000002",
        name="Synthetic Renamed Corp", exchange="XNAS", currency="USD",
        figi="BBG000000003", lei="00000000000000000003",
        history=[
            {
                "ticker": "OLDTICK",
                "change_date": "2000-01-01",
                "change_type": "none",
                "source": "synthetic",
                "source_url": "https://example.invalid/synthetic",
            },
            {
                "ticker": "NEWTICK",
                "change_date": "2022-06-09",
                "change_type": "rename",
                "source": "synthetic",
                "source_url": "https://example.invalid/synthetic",
            },
        ],
    ),
    make_instrument(
        ticker="MULTI", country="US", cusip_base="00000003",
        name="Synthetic Multi Listing", exchange="XNAS", currency="USD",
        figi="BBG000000004", lei="00000000000000000004",
        listings=[
            {
                "exchange": "XNAS",
                "ticker": "MULTI",
                "currency": "USD",
                "status": "PRIMARY",
            },
            {
                "exchange": "XETR",
                "ticker": "SYM",
                "currency": "EUR",
                "status": "SECONDARY",
            },
        ],
    ),
    make_instrument(
        ticker="DUP", country="US", cusip_base="00000004",
        name="Synthetic Dup US", exchange="XNAS", currency="USD",
        figi="BBG000000005", lei="00000000000000000005",
    ),
    make_instrument(
        ticker="DUP", country="GB", cusip_base="00000005",
        name="Synthetic Dup UK", exchange="XLON", currency="GBP",
        figi="BBG000000006", lei="00000000000000000006",
    ),
    make_instrument(
        ticker="ETFSYN", country="US", cusip_base="00000006",
        name="Synthetic ETF", exchange="XNAS", currency="USD",
        asset_class="etf",
        figi="BBG000000007", lei="00000000000000000007",
    ),
]


# ─── Emit fixture ─────────────────────────────────────────────────────

fixture = {
    "meta": {
        "version": "1.0.0",
        "generated": "2026-09-10",
        "data_valid_as_of": "2026-09-10",
        "count": len(instruments),
        "sources": ["synthetic"],
        "coverage": {
            "exchanges": sorted({i["exchange"] for i in instruments}),
            "asset_classes": sorted({i["asset_class"] for i in instruments}),
            "countries": sorted({i["isin"][:2] for i in instruments}),
        },
    },
    "instruments": instruments,
}

out_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "identifiers.test.json"
out_path.write_text(
    json.dumps(fixture, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Wrote {out_path} ({len(instruments)} instruments)")
for inst in instruments:
    print(
        f"  {inst['ticker']:8s} {inst['isin']:14s} "
        f"{inst['cusip'] or '-':10s} {inst['figi']:14s} {inst['exchange']}"
    )