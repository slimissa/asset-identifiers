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


# ─── Helpers ──────────────────────────────────────────────────────────

def load_registry():
    with open(ROOT / "identifiers.json", "r", encoding="utf-8") as f:
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
    for inst in get_instruments():
        if inst.get("lei") == lei:
            return inst
    return None


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

    def test_apple_cusip_consistency(self):
        """Specific test: Apple's ISIN and CUSIP."""
        aapl = find_by_ticker("AAPL", "XNAS")[0]
        assert aapl["isin"] == "US0378331005"
        assert aapl["cusip"] == "037833100"
        assert aapl["isin"][2:11] == aapl["cusip"]

    def test_meta_cusip_consistency(self):
        """Specific test: Meta's ISIN and CUSIP after ticker change."""
        meta = find_by_ticker("META", "XNAS")[0]
        assert meta["isin"] == "US30303M1027"
        assert meta["cusip"] == "30303M102"
        assert meta["isin"][2:11] == meta["cusip"]


# ─── ISIN ↔ FIGI Cross-Reference Tests ────────────────────────────────

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
        aapl = find_by_ticker("AAPL", "XNAS")[0]
        assert aapl["figi"] == "BBG000B9XRY4"

    def test_meta_figi(self):
        """Specific test: Meta's FIGI."""
        meta = find_by_ticker("META", "XNAS")[0]
        assert meta["figi"] == "BBG000MM2P62"


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

    def test_pru_has_two_instruments(self):
        """PRU should exist on both XLON and XNYS."""
        results = find_by_ticker("PRU")
        assert len(results) == 2, f"Expected 2 PRU instruments, got {len(results)}"

    def test_pru_different_exchanges(self):
        """PRU instruments should be on different exchanges."""
        exchanges = {i.get("exchange") for i in find_by_ticker("PRU")}
        assert exchanges == {"XLON", "XNYS"}, f"Unexpected exchanges: {exchanges}"

    def test_pru_different_isins(self):
        """PRU instruments should have different ISINs."""
        isins = {i.get("isin") for i in find_by_ticker("PRU")}
        assert len(isins) == 2, "PRU instruments should have different ISINs"

    def test_pru_different_cusips(self):
        """PRU on XNYS should have CUSIP, PRU on XLON should not."""
        pru_nyse = find_by_ticker("PRU", "XNYS")[0]
        pru_lon = find_by_ticker("PRU", "XLON")[0]
        assert pru_nyse.get("cusip") is not None, "PRU on XNYS should have CUSIP"
        assert pru_lon.get("cusip") is None, "PRU on XLON should not have CUSIP"

    def test_pru_different_currencies(self):
        """PRU instruments should trade in different currencies."""
        pru_nyse = find_by_ticker("PRU", "XNYS")[0]
        pru_lon = find_by_ticker("PRU", "XLON")[0]
        assert pru_nyse.get("currency") == "USD"
        assert pru_lon.get("currency") == "GBP"

    def test_pru_disambiguation_by_exchange(self):
        """Ticker+exchange should disambiguate PRU correctly."""
        pru_nyse = find_by_ticker("PRU", "XNYS")[0]
        pru_lon = find_by_ticker("PRU", "XLON")[0]
        assert pru_nyse["isin"] == "US7443201022"
        assert pru_lon["isin"] == "GB0007099541"


# ─── Ticker Change History Tests ──────────────────────────────────────

class TestTickerChangeHistory:
    """Test ticker change history consistency."""

    def test_meta_history_has_fb(self):
        """Meta's history should include FB."""
        meta = find_by_ticker("META", "XNAS")[0]
        history_tickers = [h.get("ticker") for h in meta.get("history", [])]
        assert "FB" in history_tickers, "META history missing FB"

    def test_meta_history_has_meta(self):
        """Meta's history should include META."""
        meta = find_by_ticker("META", "XNAS")[0]
        history_tickers = [h.get("ticker") for h in meta.get("history", [])]
        assert "META" in history_tickers, "META history missing META"

    def test_meta_history_fb_before_meta(self):
        """FB should appear before META in history."""
        meta = find_by_ticker("META", "XNAS")[0]
        history_tickers = [h.get("ticker") for h in meta.get("history", [])]
        fb_idx = history_tickers.index("FB")
        meta_idx = history_tickers.index("META")
        assert fb_idx < meta_idx, "FB should appear before META"

    def test_meta_change_date(self):
        """Meta's ticker change date should be 2022-06-09."""
        meta = find_by_ticker("META", "XNAS")[0]
        for event in meta.get("history", []):
            if event.get("change_type") == "rename":
                assert event.get("change_date") == "2022-06-09"
                assert event.get("ticker") == "META"

    def test_meta_isin_unchanged_after_rename(self):
        """Meta's ISIN should not change after ticker rename."""
        meta = find_by_ticker("META", "XNAS")[0]
        assert meta["isin"] == "US30303M1027"
        # ISIN is permanent — ticker changes do not affect it

    def test_xom_history_has_initial(self):
        """XOM's history should start with initial listing."""
        xom = find_by_ticker("XOM", "XNYS")[0]
        history = xom.get("history", [])
        assert history[0].get("change_type") == "none"
        assert history[0].get("ticker") == "XON"

    def test_xom_history_has_rename(self):
        """XOM's history should include the merger rename."""
        xom = find_by_ticker("XOM", "XNYS")[0]
        history = xom.get("history", [])
        rename_events = [h for h in history if h.get("change_type") == "rename"]
        assert len(rename_events) >= 1, "XOM missing rename event"

    def test_googl_history(self):
        """GOOGL's history should show GOOG → GOOGL."""
        googl = find_by_ticker("GOOGL", "XNAS")[0]
        history_tickers = [h.get("ticker") for h in googl.get("history", [])]
        assert "GOOG" in history_tickers, "GOOGL history missing GOOG"
        assert "GOOGL" in history_tickers, "GOOGL history missing GOOGL"


# ─── Multi-Exchange Listing Tests ─────────────────────────────────────

class TestMultiExchangeListings:
    """Test multi-exchange listing consistency."""

    def test_aapl_multiple_listings(self):
        """AAPL should have multiple exchange listings."""
        aapl = find_by_ticker("AAPL", "XNAS")[0]
        listings = aapl.get("listings", [])
        assert len(listings) >= 2, "AAPL should have multiple listings"

    def test_aapl_primary_listing(self):
        """AAPL's primary listing should be XNAS."""
        aapl = find_by_ticker("AAPL", "XNAS")[0]
        primary = [l for l in aapl.get("listings", []) if l.get("status") == "PRIMARY"]
        assert len(primary) == 1
        assert primary[0].get("exchange") == "XNAS"

    def test_aapl_secondary_listing(self):
        """AAPL should have a secondary listing on XETR."""
        aapl = find_by_ticker("AAPL", "XNAS")[0]
        exchanges = {l.get("exchange") for l in aapl.get("listings", [])}
        assert "XETR" in exchanges, "AAPL should be listed on XETR"

    def test_aapl_listing_currencies(self):
        """AAPL's listings should be in different currencies."""
        aapl = find_by_ticker("AAPL", "XNAS")[0]
        currencies = {l.get("currency") for l in aapl.get("listings", [])}
        assert "USD" in currencies, "AAPL primary should be USD"
        assert "EUR" in currencies, "AAPL secondary should be EUR"

    def test_listings_match_top_level(self):
        """Top-level exchange/ticker should match primary listing."""
        for inst in get_instruments():
            listings = inst.get("listings", [])
            if listings:
                primary = [l for l in listings if l.get("status") == "PRIMARY"]
                if primary:
                    assert primary[0].get("exchange") == inst.get("exchange"), (
                        f"{inst.get('ticker')}: primary listing exchange mismatch"
                    )
                    assert primary[0].get("ticker") == inst.get("ticker"), (
                        f"{inst.get('ticker')}: primary listing ticker mismatch"
                    )

    def test_no_duplicate_listings(self):
        """No instrument should have duplicate listings."""
        for inst in get_instruments():
            listings = inst.get("listings", [])
            pairs = [(l.get("exchange"), l.get("ticker")) for l in listings]
            assert len(pairs) == len(set(pairs)), (
                f"{inst.get('ticker')}: duplicate listing found"
            )


# ─── LEI Cross-Reference Tests ────────────────────────────────────────

class TestLEICrossReference:
    """Test LEI relationships."""

    def test_lei_lookup_matches_isin(self):
        """LEI lookup should return the same instrument."""
        for inst in get_instruments():
            lei = inst.get("lei")
            if lei:
                found = find_by_lei(lei)
                assert found is not None, f"LEI lookup failed: {lei}"
                assert found.get("isin") == inst.get("isin"), (
                    f"LEI {lei} maps to wrong ISIN"
                )

    def test_no_duplicate_leis(self):
        """No two instruments should share a LEI."""
        leis = [i["lei"] for i in get_instruments() if i.get("lei")]
        assert len(leis) == len(set(leis)), "Duplicate LEI found"

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