#!/usr/bin/env python3
"""
Asset Identifier Registry — Python usage example.

This example demonstrates all major features of the
Python wrapper for the asset identifier registry.

Run:
    cd examples
    python3 python_lookup.py

Or from the project root:
    python3 examples/python_lookup.py
"""

import sys
from pathlib import Path

# Add the wrappers/python directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "wrappers" / "python"))

from asset_identifiers import AssetRegistry


# ─── Helpers ──────────────────────────────────────────────────────────

def print_section(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("═" * 60)
    print(f"  {title}")
    print("═" * 60)


def deref_or_nil(value) -> str:
    """Return the value or 'nil' if None."""
    return value if value is not None else "nil"


# ─── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    # ─── Load the Registry ──────────────────────────────────────────

    registry_path = Path(__file__).parent.parent / "identifiers.json"
    registry = AssetRegistry(registry_path)

    print_section("Registry Overview")
    print(f"Version:     {registry.version()}")
    print(f"Generated:   {registry.generated()}")
    print(f"Instruments: {registry.count}")
    print(f"Path:        {registry.path}")
    print(f"Sources:     {registry.sources()}")

    # ─── Lookup by ISIN ─────────────────────────────────────────────

    print_section("Lookup by ISIN")

    aapl = registry.by_isin("US0378331005")
    if aapl is None:
        print("ERROR: AAPL not found")
        sys.exit(1)

    print(f"Ticker:      {aapl['ticker']}")
    print(f"Name:        {aapl['name']}")
    print(f"Exchange:    {aapl['exchange']}")
    print(f"Currency:    {aapl['currency']}")
    print(f"Asset class: {aapl['asset_class']}")
    print(f"CUSIP:       {deref_or_nil(aapl.get('cusip'))}")
    print(f"FIGI:        {deref_or_nil(aapl.get('figi'))}")
    print(f"LEI:         {deref_or_nil(aapl.get('lei'))}")
    print(f"Active:      {aapl['active']}")
    print(f"Country:     {deref_or_nil(aapl.get('country'))}")

    # ─── Lookup by Other Identifiers ────────────────────────────────

    print_section("Lookup by Other Identifiers")

    msft = registry.by_cusip("594918104")
    if msft:
        print(f"By CUSIP 594918104 → {msft['ticker']} ({msft['name']})")

    aapl_figi = registry.by_figi("BBG000B9XRY4")
    if aapl_figi:
        print(f"By FIGI BBG000B9XRY4 → {aapl_figi['ticker']} ({aapl_figi['name']})")

    aapl_lei = registry.by_lei("HWUPKR0MPOU8FGXBT394")
    if aapl_lei:
        print(f"By LEI HWUPKR... → {aapl_lei['ticker']} ({aapl_lei['name']})")

    # ─── Ticker Lookup ──────────────────────────────────────────────

    print_section("Ticker Lookup")

    aapl_ticker = registry.by_ticker("AAPL", "XNAS")
    if aapl_ticker:
        print(f"AAPL on XNAS → {aapl_ticker['isin']}")

    pru_all = registry.by_ticker("PRU")
    print(f"PRU (all exchanges): {len(pru_all)} results")
    for pru in pru_all:
        print(f"  {pru['ticker']} on {pru['exchange']} → {pru['isin']} ({pru['name']})")

    pru_london = registry.by_ticker("PRU", "XLON")
    if pru_london:
        print(f"PRU on XLON → {pru_london['isin']} ({pru_london['name']}, {pru_london['currency']})")

    pru_nyse = registry.by_ticker("PRU", "XNYS")
    if pru_nyse:
        print(f"PRU on XNYS → {pru_nyse['isin']} ({pru_nyse['name']}, {pru_nyse['currency']})")

    # ─── Filtering ──────────────────────────────────────────────────

    print_section("Filtering")

    nasdaq = registry.by_exchange("XNAS")
    print(f"NASDAQ (XNAS): {len(nasdaq)} instruments")

    etfs = registry.by_asset_class("etf")
    print(f"ETFs: {len(etfs)} instruments")
    for etf in etfs:
        print(f"  {etf['ticker']} ({etf['name']})")

    us_instruments = registry.by_country("US")
    print(f"US instruments: {len(us_instruments)}")

    usd_instruments = registry.by_currency("USD")
    print(f"USD instruments: {len(usd_instruments)}")

    # ─── Aggregate Information ──────────────────────────────────────

    print_section("Aggregate Information")

    print(f"Exchanges:   {registry.exchanges()}")
    print(f"Asset classes: {registry.asset_classes()}")
    print(f"Currencies:  {registry.currencies()}")
    print(f"Countries:   {registry.countries()}")

    # ─── Identifier Coverage ────────────────────────────────────────

    print_section("Identifier Coverage")

    coverage = registry.identifier_coverage()

    print(f"ISIN:  {coverage['isin']['covered']}/{coverage['isin']['total']} ({coverage['isin']['percentage']:.1f}%)")
    print(f"CUSIP: {coverage['cusip']['covered']}/{coverage['cusip']['total']} ({coverage['cusip']['percentage']:.1f}%)")
    print(f"SEDOL: {coverage['sedol']['covered']}/{coverage['sedol']['total']} ({coverage['sedol']['percentage']:.1f}%)")
    print(f"FIGI:  {coverage['figi']['covered']}/{coverage['figi']['total']} ({coverage['figi']['percentage']:.1f}%)")
    print(f"LEI:   {coverage['lei']['covered']}/{coverage['lei']['total']} ({coverage['lei']['percentage']:.1f}%)")

    # ─── Ticker Changes ─────────────────────────────────────────────

    print_section("Ticker Changes")

    meta = registry.by_isin("US30303M1027")
    if meta:
        print(f"Current ticker: {meta['ticker']}")
        print(f"ISIN:           {meta['isin']} (unchanged)")
        print("History:")
        for event in meta.get("history", []):
            reason = event.get("reason", "")
            print(f"  {event['ticker']}  {event['change_date']}  {event['change_type']}  ({reason})")

    # ─── Multi-Exchange Listings ────────────────────────────────────

    print_section("Multi-Exchange Listings")

    for listing in aapl.get("listings", []):
        print(f"{listing['exchange']}: {listing['ticker']} ({listing['currency']}, {listing['status']})")

    # ─── Ambiguous Tickers ──────────────────────────────────────────

    print_section("Ambiguous Tickers")

    ambiguous = registry.tickers_with_multiple_listings()
    print(f"Tickers with multiple listings: {ambiguous}")

    # ─── Existence Checks ───────────────────────────────────────────

    print_section("Existence Checks")

    print(f"US0378331005 exists: {registry.isin_exists('US0378331005')}")
    print(f"XX0000000000 exists: {registry.isin_exists('XX0000000000')}")
    print(f"AAPL on XNAS exists: {registry.ticker_exists('AAPL', 'XNAS')}")
    print(f"PRU anywhere exists: {registry.ticker_exists('PRU')}")
    print(f"ZZZZ exists:         {registry.ticker_exists('ZZZZ')}")

    # ─── Resolve (auto-detect) ──────────────────────────────────────

    print_section("Resolve (auto-detect identifier type)")

    print(f"resolve('US0378331005') → {registry.resolve('US0378331005')['ticker']}")
    print(f"resolve('037833100')    → {registry.resolve('037833100')['ticker']}")
    print(f"resolve('BBG000B9XRY4') → {registry.resolve('BBG000B9XRY4')['ticker']}")
    print(f"resolve('AAPL', 'XNAS') → {registry.resolve('AAPL', 'XNAS')['isin']}")

    # ─── Iteration ──────────────────────────────────────────────────

    print_section("Iteration (first 10)")

    for i, inst in enumerate(registry):
        if i >= 10:
            print("  ...")
            break
        print(f"  {inst['ticker']} ({inst['exchange']}): {inst['isin']}")

    # ─── String Representation ──────────────────────────────────────

    print_section("String Representation")

    print(f"{registry}")

    print()
    print("Example complete.")


if __name__ == "__main__":
    main()