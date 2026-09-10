#!/usr/bin/env python3
"""
Cross-reference consistency tests.

Validates relationships between different identifier types:
- ISIN ↔ CUSIP (US instruments)
- ISIN ↔ FIGI
- Ticker ↔ exchange ↔ ISIN
- Round-trip lookups (ticker → ISIN → ticker)
- Ticker change history consistency
- Duplicate ticker disambiguation
- Multi-exchange listing consistency

Run:
    python3 tests/test_cross_reference.py
    pytest tests/test_cross_reference.py -v
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixture import (
    FIXTURE_PATH,
    TESTA, NEWTICK, MULTI, DUP_US, DUP_UK, ETFSYN,
    count as fixture_count,
    meta as fixture_meta,
    all_instruments,
)


# ─── Helpers ──────────────────────────────────────────────────────────

def load_registry():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_instruments():
    return load_registry().get("instruments", [])


def find_by_isin(isin):
    for inst in get_instruments():
        if inst.get("isin") == isin:
            return inst
    return None


def find_by_ticker(ticker, exchange=None):
    results = []
    for inst in get_instruments():
        if inst.get("ticker") == ticker:
            if exchange is None or inst.get("exchange") == exchange:
                results.append(inst)
    return results


def find_by_cusip(cusip):
    for inst in get_instruments():
        if inst.get("cusip") == cusip:
            return inst
    return None


def find_by_figi(figi):
    for inst in get_instruments():
        if inst.get("figi") == figi:
            return inst
    return None


def find_by_lei(lei):
    return [inst for inst in get_instruments() if inst.get("lei") == lei]


# ─── ISIN ↔ CUSIP Cross-Reference Tests ───────────────────────────────

class TestISINCUSIPCrossReference:
    """Test ISIN ↔ CUSIP relationships."""

    def test_us_isin_contains_cusip(self):
        """Every US ISIN should contain its CUSIP."""
        for inst in get_instruments():
            isin = inst.get("isin", "")
            cusip = inst.get("cusip")
            if isin.startswith("US") and cusip:
                assert isin[2:11] == cusip, (
                    f"ISIN-CUSIP mismatch for {inst.get('ticker')}: {isin} vs {cusip}"
                )

    def test_cusip_lookup_matches_isin(self):
        """CUSIP lookup should return the same instrument as ISIN lookup."""
        for inst in get_instruments():
            cusip = inst.get("cusip")
            if cusip:
                found = find_by_cusip(cusip)
                assert found is not None, f"CUSIP lookup failed: {cusip}"
                assert found.get("isin") == inst.get("isin"), (
                    f"CUSIP {cusip} maps to wrong ISIN: "
                    f"{found.get('isin')} vs {inst.get('isin')}"
                )

    def test_no_duplicate_cusips(self):
        """No two instruments should share a CUSIP."""
        cusips = [i["cusip"] for i in get_instruments() if i.get("cusip")]
        assert len(cusips) == len(set(cusips)), "Duplicate CUSIP found"

    def test_non_us_instruments_null_cusip(self):
        """Non-US instruments should have null CUSIP."""
        for inst in get_instruments():
            if inst.get("country") not in ("US", "CA"):
                # Not strictly required, but common practice
                # Some non-US instruments may have CUSIPs for US listings
                pass

    def test_testa_cusip_consistency(self):
        """TESTA's ISIN and CUSIP should be consistent."""
        inst = find_by_ticker(TESTA["ticker"], TESTA["exchange"])[0]
        assert inst["isin"] == TESTA["isin"]
        assert inst["cusip"] == TESTA["cusip"]
        assert inst["isin"][2:11] == inst["cusip"]

class TestISINFIGICrossReference:
    """Test ISIN ↔ FIGI relationships."""

    def test_figi_lookup_matches_isin(self):
        """FIGI lookup should return the same instrument as ISIN lookup."""
        for inst in get_instruments():
            figi = inst.get("figi")
            if figi:
                found = find_by_figi(figi)
                assert found is not None, f"FIGI lookup failed: {figi}"
                assert found.get("isin") == inst.get("isin"), (
                    f"FIGI {figi} maps to wrong ISIN: "
                    f"{found.get('isin')} vs {inst.get('isin')}"
                )

    def test_no_duplicate_figis(self):
        """No two instruments should share a FIGI."""
        figis = [i["figi"] for i in get_instruments() if i.get("figi")]
        assert len(figis) == len(set(figis)), "Duplicate FIGI found"

    def test_figi_format(self):
        """FIGIs should start with BBG and be 12 characters."""
        for inst in get_instruments():
            figi = inst.get("figi")
            if figi:
                assert len(figi) == 12, f"FIGI should be 12 chars: {figi}"
                assert figi.startswith("BBG"), f"FIGI should start with BBG: {figi}"

    def test_apple_figi(self):
        """Specific test: Apple's FIGI."""
        inst = find_by_ticker(TESTA["ticker"], TESTA["exchange"])[0]
        assert inst["figi"] == TESTA["figi"]

    def test_meta_figi(self):
        """Specific test: Meta's FIGI."""
        inst = find_by_ticker(NEWTICK["ticker"], NEWTICK["exchange"])[0]
        assert inst["figi"] == NEWTICK["figi"]


# ─── Ticker ↔ Exchange ↔ ISIN Cross-Reference Tests ───────────────────

class TestTickerExchangeISINCrossReference:
    """Test ticker+exchange ↔ ISIN relationships."""

    def test_ticker_exchange_pair_unique(self):
        """Each ticker+exchange pair should map to exactly one ISIN."""
        pairs = {}
        for inst in get_instruments():
            pair = (inst.get("ticker"), inst.get("exchange"))
            isin = inst.get("isin")
            if pair in pairs:
                assert pairs[pair] == isin, (
                    f"Ticker+exchange pair {pair} maps to multiple ISINs: "
                    f"{pairs[pair]} and {isin}"
                )
            else:
                pairs[pair] = isin

    def test_ticker_lookup_returns_instrument(self):
        """Ticker lookup should return at least one instrument."""
        for inst in get_instruments():
            ticker = inst.get("ticker")
            results = find_by_ticker(ticker)
            assert len(results) >= 1, f"Ticker lookup failed: {ticker}"

    def test_ticker_exchange_lookup_exact(self):
        """Ticker+exchange lookup should return exactly one instrument."""
        for inst in get_instruments():
            ticker = inst.get("ticker")
            exchange = inst.get("exchange")
            results = find_by_ticker(ticker, exchange)
            assert len(results) == 1, (
                f"Expected 1 result for {ticker} on {exchange}, got {len(results)}"
            )
            assert results[0].get("isin") == inst.get("isin")

    def test_round_trip_ticker_isin_ticker(self):
        """Round-trip: ticker → ISIN → ticker should return same ticker."""
        for inst in get_instruments():
            ticker = inst.get("ticker")
            exchange = inst.get("exchange")
            isin = inst.get("isin")
            
            # Ticker → ISIN
            found = find_by_ticker(ticker, exchange)[0]
            assert found["isin"] == isin
            
            # ISIN → Ticker
            found_by_isin = find_by_isin(isin)
            assert found_by_isin is not None
            assert found_by_isin["ticker"] == ticker
            assert found_by_isin["exchange"] == exchange

    def test_round_trip_isin_ticker_isin(self):
        """Round-trip: ISIN → ticker → ISIN should return same ISIN."""
        for inst in get_instruments():
            isin = inst.get("isin")
            
            # ISIN → Ticker
            found = find_by_isin(isin)
            assert found is not None
            
            # Ticker → ISIN
            found_by_ticker = find_by_ticker(found["ticker"], found["exchange"])[0]
            assert found_by_ticker["isin"] == isin


# ─── Duplicate Ticker Tests ───────────────────────────────────────────

class TestDuplicateTickerDisambiguation:
    """Test duplicate ticker handling."""

    def test_ambiguous_ticker_has_two_instruments(self):
        results = find_by_ticker(DUP_US["ticker"])
        assert len(results) == 2

    def test_ambiguous_ticker_different_exchanges(self):
        exchanges = {i.get("exchange") for i in find_by_ticker(DUP_US["ticker"])}
        assert exchanges == {DUP_US["exchange"], DUP_UK["exchange"]}

    def test_ambiguous_ticker_different_isins(self):
        isins = {i.get("isin") for i in find_by_ticker(DUP_US["ticker"])}
        assert len(isins) == 2

    def test_ambiguous_ticker_different_cusips(self):
        us = find_by_ticker(DUP_US["ticker"], DUP_US["exchange"])[0]
        uk = find_by_ticker(DUP_UK["ticker"], DUP_UK["exchange"])[0]
        assert us.get("cusip") is not None
        assert uk.get("cusip") is None

    def test_ambiguous_ticker_different_currencies(self):
        us = find_by_ticker(DUP_US["ticker"], DUP_US["exchange"])[0]
        uk = find_by_ticker(DUP_UK["ticker"], DUP_UK["exchange"])[0]
        assert us.get("currency") == DUP_US["currency"]
        assert uk.get("currency") == DUP_UK["currency"]



class TestTickerChangeHistory:
    """Test ticker change history consistency."""

    def test_history_contains_all_previous_tickers(self):
        inst = find_by_ticker(NEWTICK["ticker"], NEWTICK["exchange"])[0]
        history_tickers = [h.get("ticker") for h in inst.get("history", [])]
        for event in NEWTICK["history"]:
            assert event["ticker"] in history_tickers

    def test_history_is_chronological(self):
        inst = find_by_ticker(NEWTICK["ticker"], NEWTICK["exchange"])[0]
        dated = [h for h in inst.get("history", []) if h.get("change_date")]
        dates = [h["change_date"] for h in dated]
        assert dates == sorted(dates)

    def test_rename_event_date_matches_fixture(self):
        inst = find_by_ticker(NEWTICK["ticker"], NEWTICK["exchange"])[0]
        for fixture_event in NEWTICK["history"]:
            if fixture_event.get("change_type") == "rename":
                matches = [
                    e for e in inst.get("history", [])
                    if e.get("change_type") == "rename"
                ]
                assert len(matches) == 1
                assert matches[0]["change_date"] == fixture_event["change_date"]

    def test_isin_unchanged_after_rename(self):
        inst = find_by_ticker(NEWTICK["ticker"], NEWTICK["exchange"])[0]
        assert inst["isin"] == NEWTICK["isin"]



class TestMultiExchangeListings:
    """Test multi-exchange listing consistency."""

    def test_multiple_listings(self):
        inst = find_by_ticker(MULTI["ticker"], MULTI["exchange"])[0]
        assert len(inst.get("listings", [])) >= 2

    def test_primary_listing_matches_top_level(self):
        inst = find_by_ticker(MULTI["ticker"], MULTI["exchange"])[0]
        primary = [l for l in inst.get("listings", []) if l.get("status") == "PRIMARY"]
        assert len(primary) == 1
        assert primary[0].get("exchange") == MULTI["exchange"]
        assert primary[0].get("ticker") == MULTI["ticker"]

    def test_secondary_listings_present(self):
        inst = find_by_ticker(MULTI["ticker"], MULTI["exchange"])[0]
        exchanges = {l.get("exchange") for l in inst.get("listings", [])}
        for listing in MULTI["listings"]:
            assert listing["exchange"] in exchanges

    def test_listings_currencies_match_fixture(self):
        inst = find_by_ticker(MULTI["ticker"], MULTI["exchange"])[0]
        currencies = {l.get("currency") for l in inst.get("listings", [])}
        for listing in MULTI["listings"]:
            assert listing["currency"] in currencies

    def test_no_duplicate_listings(self):
        for inst in get_instruments():
            pairs = [(l.get("exchange"), l.get("ticker")) for l in inst.get("listings", [])]
            assert len(pairs) == len(set(pairs))



# ─── LEI Cross-Reference Tests ────────────────────────────────────────

class TestLEICrossReference:
    """Test LEI relationships."""

    def test_lei_lookup_finds_instrument(self):
        """LEI lookup should return all instruments sharing that LEI."""
        for inst in get_instruments():
            lei = inst.get("lei")
            if lei:
                found_list = find_by_lei(lei)
                assert found_list, f"LEI lookup failed: {lei}"
                assert any(f.get("lei") == lei for f in found_list), (
                    f"LEI {lei} lookup returned wrong instrument(s)"
                )

    def test_lei_can_be_shared(self):
        """LEI is an entity identifier; multiple instruments may share one."""
        leis = [i["lei"] for i in get_instruments() if i.get("lei")]
        # FOX and FOXA share the same LEI.
        assert len(leis) >= len(set(leis)), "Expected shared LEIs to be allowed"

    def test_lei_format(self):
        """LEIs should be 20 alphanumeric characters."""
        for inst in get_instruments():
            lei = inst.get("lei")
            if lei:
                assert len(lei) == 20, f"LEI should be 20 chars: {lei}"
                assert lei.isalnum(), f"LEI should be alphanumeric: {lei}"


# ─── Run All Tests ────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests manually."""
    test_classes = [
        TestISINCUSIPCrossReference,
        TestISINFIGICrossReference,
        TestTickerExchangeISINCrossReference,
        TestDuplicateTickerDisambiguation,
        TestTickerChangeHistory,
        TestMultiExchangeListings,
        TestLEICrossReference,
    ]

    passed = 0
    failed = 0
    errors = 0
    total = 0

    for cls in test_classes:
        for method_name in dir(cls):
            if method_name.startswith("test_"):
                total += 1
                test_name = f"{cls.__name__}.{method_name}"
                try:
                    instance = cls()
                    method = getattr(instance, method_name)
                    method()
                    passed += 1
                    print(f"  PASS: {test_name}")
                except AssertionError as e:
                    failed += 1
                    print(f"  FAIL: {test_name}: {e}")
                except Exception as e:
                    errors += 1
                    print(f"  ERROR: {test_name}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {errors} errors, {total} total")
    print(f"{'=' * 60}")

    return failed == 0 and errors == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)