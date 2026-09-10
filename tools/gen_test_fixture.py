#!/usr/bin/env python3
"""Generate a synthetic test fixture for the asset-identifiers registry.

All identifiers are fake but pass check-digit validation. Used only for tests.
"""
import json
from pathlib import Path


def cusip_check(base8: str) -> str:
    assert len(base8) == 8, "base must be 8 chars"
    total = 0
    for i, ch in enumerate(base8):
        v = int(ch) if ch.isdigit() else ord(ch.upper()) - ord('A') + 10
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return str((10 - (total % 10)) % 10)


def isin_check(first11: str) -> str:
    assert len(first11) == 11, "first11 must be 11 chars"
    digits = ''.join(
        ch if ch.isdigit() else str(ord(ch.upper()) - ord('A') + 10)
        for ch in first11
    )
    total = 0
    for i, ch in enumerate(reversed(digits)):
        v = int(ch)
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return str((10 - (total % 10)) % 10)


def make_instrument(ticker, country, cusip_base, name, exchange, currency,
                    asset_class="equity", figi="BBG000000001",
                    lei="00000000000000000001", listings=None, history=None,
                    active=True):
    cusip = cusip_base + cusip_check(cusip_base)
    isin = country + cusip + isin_check(country + cusip)
    inst = {
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
        "active": active,
        "listings": listings or [{
            "exchange": exchange, "ticker": ticker,
            "currency": currency, "is_primary": True,
        }],
        "history": history or [{
            "ticker": ticker, "change_date": None, "change_type": "none",
        }],
    }
    return inst


instruments = [
    # Basic US instrument
    make_instrument(
        ticker="TESTA", country="US", cusip_base="00000000",
        name="Synthetic Test A", exchange="XNAS", currency="USD",
        figi="BBG000000001", lei="00000000000000000001",
    ),
    # Second basic US instrument
    make_instrument(
        ticker="TESTB", country="US", cusip_base="00000001",
        name="Synthetic Test B", exchange="XNAS", currency="USD",
        figi="BBG000000002", lei="00000000000000000002",
    ),
    # Renamed instrument (history: OLDTICK -> NEWTICK)
    make_instrument(
        ticker="NEWTICK", country="US", cusip_base="00000002",
        name="Synthetic Renamed Corp", exchange="XNAS", currency="USD",
        figi="BBG000000003", lei="00000000000000000003",
        history=[
            {"ticker": "OLDTICK", "change_date": None, "change_type": "none"},
            {"ticker": "NEWTICK", "change_date": "2020-06-01",
             "change_type": "ticker_change"},
        ],
    ),
    # Multi-exchange US instrument
    make_instrument(
        ticker="MULTI", country="US", cusip_base="00000003",
        name="Synthetic Multi Listing", exchange="XNAS", currency="USD",
        figi="BBG000000004", lei="00000000000000000004",
        listings=[
            {"exchange": "XNAS", "ticker": "MULTI", "currency": "USD",
             "is_primary": True},
            {"exchange": "XETR", "ticker": "SYM", "currency": "EUR",
             "is_primary": False},
        ],
    ),
    # Duplicate ticker, US side
    make_instrument(
        ticker="DUP", country="US", cusip_base="00000004",
        name="Synthetic Dup US", exchange="XNAS", currency="USD",
        figi="BBG000000005", lei="00000000000000000005",
    ),
    # Duplicate ticker, UK side
    make_instrument(
        ticker="DUP", country="GB", cusip_base="00000005",
        name="Synthetic Dup UK", exchange="XLON", currency="GBP",
        figi="BBG000000006", lei="00000000000000000006",
    ),
    # ETF
    make_instrument(
        ticker="ETFSYN", country="US", cusip_base="00000006",
        name="Synthetic ETF", exchange="XNAS", currency="USD",
        asset_class="etf",
        figi="BBG000000007", lei="00000000000000000007",
    ),
]

fixture = {
    "meta": {
        "version": "0.0.0-test",
        "generated": "2026-09-10",
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

out = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
out.mkdir(parents=True, exist_ok=True)
(out / "identifiers.test.json").write_text(
    json.dumps(fixture, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print(f"Wrote {out / 'identifiers.test.json'} ({len(instruments)} instruments)")