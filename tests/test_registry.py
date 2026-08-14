#!/usr/bin/env python3
"""
Registry data validation tests.

Tests cover:
- Full registry validation against schema
- Required fields for every instrument
- Check-digit validation for ISIN, CUSIP, SEDOL
- Uniqueness constraints (ISIN, CUSIP, SEDOL, FIGI, ticker+exchange)
- Cross-field business rules (country identifiers, active/delisted consistency)
- Temporal consistency (history ordering, listing/delisting dates)
- Metadata correctness (count, version, coverage)
- Distribution artifact consistency
- Historical ticker change validation
- Corporate action validation

Run:
    python3 tests/test_registry.py
    pytest tests/test_registry.py -v
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from validate import (
    validate_registry,
    validate_isin_check_digit,
    validate_cusip_check_digit,
    validate_sedol_check_digit,
)


# ─── Helper functions ─────────────────────────────────────────────────

def load_registry():
    """Load identifiers.json."""
    with open(ROOT / "identifiers.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_schema():
    """Load schema.json."""
    with open(ROOT / "schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_instruments():
    """Get instruments from registry."""
    return load_registry().get("instruments", [])


# ─── Registry Structure Tests ─────────────────────────────────────────

class TestRegistryStructure:
    """Test the overall structure of the registry."""

    def test_registry_file_exists(self):
        assert (ROOT / "identifiers.json").exists(), "identifiers.json not found"

    def test_schema_file_exists(self):
        assert (ROOT / "schema.json").exists(), "schema.json not found"

    def test_registry_is_valid_json(self):
        data = load_registry()
        assert isinstance(data, dict), "Registry should be a JSON object"

    def test_registry_has_meta(self):
        data = load_registry()
        assert "meta" in data, "Missing 'meta' object"

    def test_registry_has_instruments(self):
        data = load_registry()
        assert "instruments" in data, "Missing 'instruments' array"

    def test_instruments_is_array(self):
        instruments = get_instruments()
        assert isinstance(instruments, list), "instruments should be an array"

    def test_registry_not_empty(self):
        instruments = get_instruments()
        assert len(instruments) >= 1, "Registry should have at least 1 instrument"

    def test_full_validation_passes(self):
        success, errors = validate_registry(ROOT / "identifiers.json", ROOT / "schema.json")
        assert success, f"Registry failed validation: {errors}"


# ─── Metadata Tests ───────────────────────────────────────────────────

class TestMetaData:
    """Test registry metadata."""

    def test_meta_version_present(self):
        meta = load_registry().get("meta", {})
        assert "version" in meta, "Missing meta.version"

    def test_meta_version_format(self):
        version = load_registry().get("meta", {}).get("version", "")
        parts = version.split(".")
        assert len(parts) == 3, f"Version should be semver: {version}"
        assert all(p.isdigit() for p in parts), f"Version parts should be numeric: {version}"

    def test_meta_generated_present(self):
        meta = load_registry().get("meta", {})
        assert "generated" in meta, "Missing meta.generated"

    def test_meta_generated_is_date(self):
        generated = load_registry().get("meta", {}).get("generated", "")
        try:
            datetime.strptime(generated, "%Y-%m-%d")
        except ValueError:
            assert False, f"meta.generated should be YYYY-MM-DD: {generated}"

    def test_meta_count_present(self):
        meta = load_registry().get("meta", {})
        assert "count" in meta, "Missing meta.count"

    def test_meta_count_is_integer(self):
        count = load_registry().get("meta", {}).get("count")
        assert isinstance(count, int), "meta.count should be an integer"

    def test_meta_count_matches_actual(self):
        declared = load_registry().get("meta", {}).get("count")
        actual = len(get_instruments())
        assert declared == actual, f"meta.count ({declared}) != actual ({actual})"

    def test_meta_sources_present(self):
        sources = load_registry().get("meta", {}).get("sources", [])
        assert len(sources) >= 1, "No data sources listed"

    def test_meta_sources_not_empty_strings(self):
        sources = load_registry().get("meta", {}).get("sources", [])
        for source in sources:
            assert len(source.strip()) >= 1, "Source should not be empty"

    def test_meta_coverage_present(self):
        coverage = load_registry().get("meta", {}).get("coverage", {})
        assert isinstance(coverage, dict), "meta.coverage should be an object"

    def test_meta_coverage_exchanges(self):
        coverage = load_registry().get("meta", {}).get("coverage", {})
        exchanges = coverage.get("exchanges", [])
        actual_exchanges = set(i.get("exchange") for i in get_instruments())
        for exchange in actual_exchanges:
            assert exchange in exchanges, f"Exchange {exchange} not in coverage"

    def test_meta_coverage_asset_classes(self):
        coverage = load_registry().get("meta", {}).get("coverage", {})
        classes = coverage.get("asset_classes", [])
        actual_classes = set(i.get("asset_class") for i in get_instruments())
        for asset_class in actual_classes:
            assert asset_class in classes, f"Asset class {asset_class} not in coverage"

    def test_meta_coverage_countries(self):
        coverage = load_registry().get("meta", {}).get("coverage", {})
        countries = coverage.get("countries", [])
        actual_countries = set(i.get("country") for i in get_instruments() if i.get("country"))
        for country in actual_countries:
            assert country in countries, f"Country {country} not in coverage"


# ─── Required Fields Tests ────────────────────────────────────────────

class TestRequiredFields:
    """Test required fields for every instrument."""

    REQUIRED_FIELDS = [
        "isin", "ticker", "exchange", "name", "currency",
        "asset_class", "active",
    ]

    def test_all_required_fields_present(self):
        for instrument in get_instruments():
            ticker = instrument.get("ticker", "?")
            for field in self.REQUIRED_FIELDS:
                assert field in instrument, f"{ticker}: missing required field '{field}'"

    def test_isin_not_null(self):
        for instrument in get_instruments():
            assert instrument.get("isin"), f"{instrument.get('ticker', '?')}: isin is null"

    def test_ticker_not_null(self):
        for instrument in get_instruments():
            assert instrument.get("ticker"), "Instrument with null ticker"

    def test_exchange_not_null(self):
        for instrument in get_instruments():
            assert instrument.get("exchange"), f"{instrument.get('ticker', '?')}: exchange is null"

    def test_name_not_null(self):
        for instrument in get_instruments():
            assert instrument.get("name"), f"{instrument.get('ticker', '?')}: name is null"

    def test_currency_not_null(self):
        for instrument in get_instruments():
            assert instrument.get("currency"), f"{instrument.get('ticker', '?')}: currency is null"

    def test_active_is_boolean(self):
        for instrument in get_instruments():
            active = instrument.get("active")
            assert isinstance(active, bool), f"{instrument.get('ticker', '?')}: active should be boolean"

    def test_ticker_length(self):
        for instrument in get_instruments():
            ticker = instrument.get("ticker", "")
            assert 1 <= len(ticker) <= 16, f"Invalid ticker length: {ticker}"

    def test_exchange_format(self):
        for instrument in get_instruments():
            exchange = instrument.get("exchange", "")
            assert len(exchange) == 4, f"{instrument.get('ticker', '?')}: MIC should be 4 chars"
            assert exchange.isalnum(), f"{instrument.get('ticker', '?')}: MIC not alphanumeric"

    def test_currency_format(self):
        for instrument in get_instruments():
            currency = instrument.get("currency", "")
            assert len(currency) == 3, f"{instrument.get('ticker', '?')}: currency should be 3 chars"
            assert currency.isalpha(), f"{instrument.get('ticker', '?')}: currency not alphabetic"
            assert currency == currency.upper(), f"{instrument.get('ticker', '?')}: currency should be uppercase"

    def test_asset_class_valid(self):
        valid_classes = {"equity", "etf", "bond", "option", "future", "other"}
        for instrument in get_instruments():
            asset_class = instrument.get("asset_class", "")
            assert asset_class in valid_classes, (
                f"{instrument.get('ticker', '?')}: invalid asset class '{asset_class}'"
            )

    def test_name_length(self):
        for instrument in get_instruments():
            name = instrument.get("name", "")
            assert len(name) >= 1, "Instrument with empty name"


# ─── Identifier Validation Tests ──────────────────────────────────────

class TestIdentifierValidation:
    """Test identifier check digits for all instruments."""

    def test_all_isins_valid(self):
        for instrument in get_instruments():
            isin = instrument.get("isin")
            assert validate_isin_check_digit(isin), (
                f"Invalid ISIN: {isin} (ticker: {instrument.get('ticker', '?')})"
            )

    def test_all_cusips_valid(self):
        for instrument in get_instruments():
            cusip = instrument.get("cusip")
            if cusip:
                assert validate_cusip_check_digit(cusip), (
                    f"Invalid CUSIP: {cusip} (ticker: {instrument.get('ticker', '?')})"
                )

    def test_all_sedols_valid(self):
        for instrument in get_instruments():
            sedol = instrument.get("sedol")
            if sedol:
                assert validate_sedol_check_digit(sedol), (
                    f"Invalid SEDOL: {sedol} (ticker: {instrument.get('ticker', '?')})"
                )

    def test_isin_length(self):
        for instrument in get_instruments():
            isin = instrument.get("isin", "")
            assert len(isin) == 12, f"ISIN should be 12 chars: {isin}"

    def test_cusip_length(self):
        for instrument in get_instruments():
            cusip = instrument.get("cusip")
            if cusip:
                assert len(cusip) == 9, f"CUSIP should be 9 chars: {cusip}"

    def test_sedol_length(self):
        for instrument in get_instruments():
            sedol = instrument.get("sedol")
            if sedol:
                assert len(sedol) == 7, f"SEDOL should be 7 chars: {sedol}"

    def test_us_isin_contains_cusip(self):
        for instrument in get_instruments():
            isin = instrument.get("isin", "")
            cusip = instrument.get("cusip")
            if isin.startswith("US") and cusip:
                assert isin[2:11] == cusip, (
                    f"US ISIN should contain CUSIP: {isin} vs {cusip}"
                )

    def test_lei_format_if_present(self):
        for instrument in get_instruments():
            lei = instrument.get("lei")
            if lei:
                assert len(lei) == 20, f"LEI should be 20 chars: {lei}"
                assert lei.isalnum(), f"LEI should be alphanumeric: {lei}"


# ─── Uniqueness Tests ─────────────────────────────────────────────────

class TestUniqueness:
    """Test uniqueness constraints."""

    def test_unique_isins(self):
        isins = [i["isin"] for i in get_instruments() if i.get("isin")]
        assert len(isins) == len(set(isins)), "Duplicate ISIN found"

    def test_unique_cusips(self):
        cusips = [i["cusip"] for i in get_instruments() if i.get("cusip")]
        assert len(cusips) == len(set(cusips)), "Duplicate CUSIP found"

    def test_unique_sedols(self):
        sedols = [i["sedol"] for i in get_instruments() if i.get("sedol")]
        assert len(sedols) == len(set(sedols)), "Duplicate SEDOL found"

    def test_unique_figis(self):
        figis = [i["figi"] for i in get_instruments() if i.get("figi")]
        assert len(figis) == len(set(figis)), "Duplicate FIGI found"

    def test_unique_leis(self):
        leis = [i["lei"] for i in get_instruments() if i.get("lei")]
        assert len(leis) == len(set(leis)), "Duplicate LEI found"

    def test_unique_ticker_exchange_pairs(self):
        pairs = [(i["ticker"], i["exchange"]) for i in get_instruments()]
        assert len(pairs) == len(set(pairs)), "Duplicate ticker+exchange pair found"


# ─── Business Rules Tests ─────────────────────────────────────────────

class TestBusinessRules:
    """Test cross-field business rules."""

    def test_us_instruments_have_cusip(self):
        for instrument in get_instruments():
            if instrument.get("country") == "US":
                assert instrument.get("cusip"), (
                    f"{instrument.get('ticker', '?')}: US instrument missing CUSIP"
                )

    def test_active_instruments_no_delisting(self):
        for instrument in get_instruments():
            if instrument.get("active") == True:
                assert instrument.get("delisting_date") is None, (
                    f"{instrument.get('ticker', '?')}: active but has delisting_date"
                )

    def test_inactive_instruments_have_delisting(self):
        for instrument in get_instruments():
            if instrument.get("active") == False:
                assert instrument.get("delisting_date") is not None, (
                    f"{instrument.get('ticker', '?')}: inactive but no delisting_date"
                )

    def test_listing_before_delisting(self):
        for instrument in get_instruments():
            listing = instrument.get("listing_date")
            delisting = instrument.get("delisting_date")
            if listing and delisting:
                assert listing <= delisting, (
                    f"{instrument.get('ticker', '?')}: listing after delisting"
                )

    def test_listings_contains_primary(self):
        for instrument in get_instruments():
            listings = instrument.get("listings", [])
            if listings:
                primary = [l for l in listings if l.get("status") == "PRIMARY"]
                assert len(primary) == 1, (
                    f"{instrument.get('ticker', '?')}: should have exactly 1 PRIMARY listing"
                )
                assert primary[0].get("exchange") == instrument.get("exchange"), (
                    f"{instrument.get('ticker', '?')}: PRIMARY listing exchange mismatch"
                )
                assert primary[0].get("ticker") == instrument.get("ticker"), (
                    f"{instrument.get('ticker', '?')}: PRIMARY listing ticker mismatch"
                )

    def test_listing_dates_consistent(self):
        for instrument in get_instruments():
            listings = instrument.get("listings", [])
            for listing in listings:
                listing_date = listing.get("listing_date")
                delisting_date = listing.get("delisting_date")
                if listing_date and delisting_date:
                    assert listing_date <= delisting_date, (
                        f"{instrument.get('ticker', '?')}: listing date after delisting date"
                    )


# ─── Temporal Consistency Tests ───────────────────────────────────────

class TestTemporalConsistency:
    """Test history and date consistency."""

    def test_history_events_ordered(self):
        for instrument in get_instruments():
            history = instrument.get("history", [])
            if history:
                dates = [h.get("change_date") for h in history if h.get("change_date")]
                assert dates == sorted(dates), (
                    f"{instrument.get('ticker', '?')}: history not chronological"
                )

    def test_history_first_event_is_none(self):
        for instrument in get_instruments():
            history = instrument.get("history", [])
            if history:
                assert history[0].get("change_type") == "none", (
                    f"{instrument.get('ticker', '?')}: first history event should be 'none'"
                )

    def test_history_last_ticker_matches(self):
        for instrument in get_instruments():
            ticker = instrument.get("ticker")
            history = instrument.get("history", [])
            if history:
                assert history[-1].get("ticker") == ticker, (
                    f"{ticker}: last history ticker ({history[-1].get('ticker')}) doesn't match"
                )

    def test_history_source_present(self):
        for instrument in get_instruments():
            history = instrument.get("history", [])
            for event in history:
                if event.get("change_type") != "none":
                    assert event.get("source"), (
                        f"{instrument.get('ticker', '?')}: change event missing source"
                    )

    def test_corporate_actions_ordered(self):
        for instrument in get_instruments():
            actions = instrument.get("corporate_actions", [])
            if actions:
                dates = [a.get("date") for a in actions if a.get("date")]
                assert dates == sorted(dates), (
                    f"{instrument.get('ticker', '?')}: corporate actions not chronological"
                )

    def test_corporate_action_types_valid(self):
        valid_types = {
            "SPLIT", "REVERSE_SPLIT", "DIVIDEND", "SPINOFF",
            "MERGER", "ACQUISITION", "RIGHTS_ISSUE", "BUYBACK",
        }
        for instrument in get_instruments():
            for action in instrument.get("corporate_actions", []):
                action_type = action.get("action_type")
                assert action_type in valid_types, (
                    f"{instrument.get('ticker', '?')}: invalid action type '{action_type}'"
                )

    def test_split_has_ratio(self):
        for instrument in get_instruments():
            for action in instrument.get("corporate_actions", []):
                if action.get("action_type") in ("SPLIT", "REVERSE_SPLIT"):
                    assert action.get("ratio"), (
                        f"{instrument.get('ticker', '?')}: split missing ratio"
                    )


# ─── Distribution Artifact Tests ──────────────────────────────────────

class TestDistributionArtifact:
    """Test the built distribution artifact."""

    def test_dist_file_exists(self):
        dist_path = ROOT / "identifiers.dist.json"
        assert dist_path.exists(), "identifiers.dist.json not found"

    def test_dist_matches_source(self):
        dist_path = ROOT / "identifiers.dist.json"
        if dist_path.exists():
            with open(dist_path, "r", encoding="utf-8") as f:
                dist = json.load(f)
            source = load_registry()
            assert len(dist.get("instruments", [])) == len(source.get("instruments", [])), (
                "Distribution artifact has different instrument count"
            )

    def test_minified_exists(self):
        min_path = ROOT / "identifiers.dist.min.json"
        assert min_path.exists(), "identifiers.dist.min.json not found"

    def test_minified_matches_source(self):
        min_path = ROOT / "identifiers.dist.min.json"
        if min_path.exists():
            with open(min_path, "r", encoding="utf-8") as f:
                minified = json.load(f)
            source = load_registry()
            assert len(minified.get("instruments", [])) == len(source.get("instruments", [])), (
                "Minified artifact has different instrument count"
            )


# ─── Ticker Change Tests ──────────────────────────────────────────────

class TestTickerChanges:
    """Test historical ticker changes."""

    def test_meta_has_ticker_change(self):
        meta = [i for i in get_instruments() if i.get("ticker") == "META"]
        assert len(meta) == 1, "META not found in registry"

    def test_meta_history_contains_fb(self):
        meta = [i for i in get_instruments() if i.get("ticker") == "META"][0]
        history_tickers = [h.get("ticker") for h in meta.get("history", [])]
        assert "FB" in history_tickers, "META history should contain FB"

    def test_meta_change_date(self):
        meta = [i for i in get_instruments() if i.get("ticker") == "META"][0]
        for event in meta.get("history", []):
            if event.get("ticker") == "META" and event.get("change_type") == "rename":
                assert event.get("change_date") == "2022-06-09", (
                    f"Expected 2022-06-09, got {event.get('change_date')}"
                )

    def test_duplicate_ticker_prudential(self):
        prus = [i for i in get_instruments() if i.get("ticker") == "PRU"]
        assert len(prus) == 2, "Should have 2 PRU instruments"

    def test_prudential_different_isins(self):
        prus = [i for i in get_instruments() if i.get("ticker") == "PRU"]
        isins = {p.get("isin") for p in prus}
        assert len(isins) == 2, "PRU instruments should have different ISINs"

    def test_prudential_different_exchanges(self):
        prus = [i for i in get_instruments() if i.get("ticker") == "PRU"]
        exchanges = {p.get("exchange") for p in prus}
        assert exchanges == {"XLON", "XNYS"}, f"Expected XLON and XNYS, got {exchanges}"


# ─── Multi-Exchange Listing Tests ─────────────────────────────────────

class TestMultiExchangeListings:
    """Test instruments with multiple exchange listings."""

    def test_aapl_has_multiple_listings(self):
        aapl = [i for i in get_instruments() if i.get("ticker") == "AAPL"][0]
        listings = aapl.get("listings", [])
        assert len(listings) >= 2, "AAPL should have multiple listings"

    def test_aapl_listing_exchanges(self):
        aapl = [i for i in get_instruments() if i.get("ticker") == "AAPL"][0]
        exchanges = {l.get("exchange") for l in aapl.get("listings", [])}
        assert "XNAS" in exchanges, "AAPL should be listed on XNAS"
        assert "XETR" in exchanges, "AAPL should be listed on XETR"

    def test_aapl_primary_listing(self):
        aapl = [i for i in get_instruments() if i.get("ticker") == "AAPL"][0]
        primary = [l for l in aapl.get("listings", []) if l.get("status") == "PRIMARY"]
        assert len(primary) == 1, "AAPL should have 1 primary listing"
        assert primary[0].get("exchange") == "XNAS"


# ─── Run All Tests ────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests manually without pytest."""
    test_classes = [
        TestRegistryStructure,
        TestMetaData,
        TestRequiredFields,
        TestIdentifierValidation,
        TestUniqueness,
        TestBusinessRules,
        TestTemporalConsistency,
        TestDistributionArtifact,
        TestTickerChanges,
        TestMultiExchangeListings,
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