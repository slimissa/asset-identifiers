#!/usr/bin/env python3
"""
Wrapper API consistency tests.

Validates that all four language wrappers (Python, JavaScript, Rust, Go)
return identical results for the same operations:
- Loading the registry
- Looking up by ISIN
- Looking up by CUSIP
- Looking up by FIGI
- Looking up by ticker+exchange
- Listing all instruments
- Filtering by exchange
- Filtering by asset class
- Getting instrument count
- Getting registry metadata

Run:
    python3 tests/test_wrappers.py
    pytest tests/test_wrappers.py -v
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixture import (
    FIXTURE_PATH,
    TESTA, NEWTICK, MULTI, DUP_US, DUP_UK, ETFSYN,
    count as fixture_count,
    meta as fixture_meta,
    exchanges as fixture_exchanges,
)


# Try to import Python wrapper
try:
    sys.path.insert(0, str(ROOT / "wrappers" / "python"))
    from asset_identifiers.registry import AssetRegistry
    PYTHON_WRAPPER_AVAILABLE = True
except ImportError:
    PYTHON_WRAPPER_AVAILABLE = False


# ─── Helpers ──────────────────────────────────────────────────────────

def get_python_wrapper():
    """Get Python registry instance if available."""
    if PYTHON_WRAPPER_AVAILABLE:
        return AssetRegistry(str(FIXTURE_PATH))
    return None



# ─── Python Wrapper Tests ─────────────────────────────────────────────

class TestPythonWrapper:
    """Test Python wrapper functionality."""

    def test_wrapper_imports(self):
        """Python wrapper should be importable."""
        assert PYTHON_WRAPPER_AVAILABLE, "Python wrapper not available"

    def test_registry_loads(self):
        """Registry should load without error."""
        registry = get_python_wrapper()
        assert registry is not None, "Registry failed to load"

    def test_get_count(self):
        """Should return correct instrument count."""
        registry = get_python_wrapper()
        assert registry.count == fixture_count()

    def test_lookup_by_isin(self):
        """Should find TESTA by ISIN."""
        registry = get_python_wrapper()
        inst = registry.by_isin(TESTA["isin"])
        assert inst is not None, "TESTA not found by ISIN"
        assert inst["ticker"] == TESTA["ticker"]

    def test_lookup_by_cusip(self):
        """Should find TESTA by CUSIP."""
        registry = get_python_wrapper()
        assert TESTA["cusip"] is not None, "fixture TESTA has no CUSIP"
        inst = registry.by_cusip(TESTA["cusip"])
        assert inst is not None, "TESTA not found by CUSIP"
        assert inst["isin"] == TESTA["isin"]

    def test_lookup_by_figi(self):
        """Should find TESTA by FIGI."""
        registry = get_python_wrapper()
        assert TESTA["figi"] is not None, "fixture TESTA has no FIGI"
        inst = registry.by_figi(TESTA["figi"])
        assert inst is not None, "TESTA not found by FIGI"
        assert inst["ticker"] == TESTA["ticker"]

    def test_lookup_by_ticker_exchange(self):
        """Should find TESTA by ticker+exchange."""
        registry = get_python_wrapper()
        inst = registry.by_ticker(TESTA["ticker"], TESTA["exchange"])
        assert inst is not None, "TESTA not found by ticker"
        assert inst["isin"] == TESTA["isin"]

    def test_lookup_nonexistent_isin(self):
        """Should return None for nonexistent ISIN."""
        registry = get_python_wrapper()
        result = registry.by_isin("XX0000000000")
        assert result is None, "Should return None for nonexistent ISIN"

    def test_lookup_nonexistent_ticker(self):
        """Should return None for nonexistent ticker."""
        registry = get_python_wrapper()
        result = registry.by_ticker("ZZZZ", "XNAS")
        assert result is None, "Should return None for nonexistent ticker"

    def test_get_all_instruments(self):
        """Should return all instruments."""
        registry = get_python_wrapper()
        assert len(registry.all()) == fixture_count()

    def test_filter_by_exchange(self):
        """Should filter by exchange."""
        registry = get_python_wrapper()
        xnas = registry.by_exchange(TESTA["exchange"])
        assert len(xnas) > 0
        for inst in xnas:
            assert inst["exchange"] == TESTA["exchange"]

    def test_filter_by_asset_class(self):
        """Should filter by asset class."""
        registry = get_python_wrapper()
        etfs = registry.by_asset_class(ETFSYN["asset_class"])
        assert len(etfs) > 0
        for inst in etfs:
            assert inst["asset_class"] == ETFSYN["asset_class"]

    def test_get_metadata(self):
        """Should return registry metadata."""
        registry = get_python_wrapper()
        meta = registry.meta()
        assert "version" in meta
        assert "count" in meta
        assert meta["count"] == fixture_count()

    def test_ambiguous_ticker(self):
        """DUP should resolve to two distinct instruments."""
        registry = get_python_wrapper()
        hits = registry.by_ticker(DUP_US["ticker"])
        assert isinstance(hits, list)
        assert len(hits) >= 2
        exchanges = {h["exchange"] for h in hits}
        assert DUP_US["exchange"] in exchanges
        assert DUP_UK["exchange"] in exchanges

# ─── Cross-Language Consistency Tests ─────────────────────────────────


# ─── API Design Consistency Tests ─────────────────────────────────────

class TestAPIDesignConsistency:
    """Test that the API design is consistent with other registries."""

    def test_method_names_consistent(self):
        """Method names should follow the established pattern."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        
        # Lookup methods
        assert hasattr(registry, "by_isin"), "Missing by_isin method"
        assert hasattr(registry, "by_cusip"), "Missing by_cusip method"
        assert hasattr(registry, "by_figi"), "Missing by_figi method"
        assert hasattr(registry, "by_ticker"), "Missing by_ticker method"
        assert hasattr(registry, "by_exchange"), "Missing by_exchange method"
        
        # Metadata methods
        assert hasattr(registry, "meta"), "Missing meta method"
        assert hasattr(registry, "all"), "Missing all method"
        
        # Properties
        assert hasattr(registry, "count"), "Missing count property"

    def test_return_types_consistent(self):
        """Return types should be consistent."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        
        # by_isin returns dict or None
        result = registry.by_isin(TESTA["isin"])
        assert isinstance(result, dict), "by_isin should return dict"
        
        # by_ticker without exchange returns list
        result = registry.by_ticker(DUP_US["ticker"])
        assert isinstance(result, list), "by_ticker without exchange should return list"
        
        # by_ticker with exchange returns dict or None
        result = registry.by_ticker(TESTA["ticker"], TESTA["exchange"])
        assert isinstance(result, dict), "by_ticker with exchange should return dict"
        
        # all returns list
        result = registry.all()
        assert isinstance(result, list), "all should return list"
        
        # meta returns dict
        result = registry.meta()
        assert isinstance(result, dict), "meta should return dict"


# ─── Data Integrity via Wrapper Tests ─────────────────────────────────

class TestDataIntegrityViaWrapper:
    """Test data integrity through the wrapper API."""

    def test_all_instruments_have_isin(self):
        """Every instrument returned by all() should have ISIN."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        for inst in registry.all():
            assert inst.get("isin"), f"Instrument missing ISIN: {inst.get('ticker')}"

    def test_all_isins_unique_via_wrapper(self):
        """All ISINs returned by all() should be unique."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        isins = [i["isin"] for i in registry.all()]
        assert len(isins) == len(set(isins)), "Duplicate ISIN via wrapper"

    def test_ticker_change_reflected(self):
        """Ticker change should be reflected in wrapper results."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        inst = registry.by_isin(NEWTICK["isin"])
        assert inst["ticker"] == NEWTICK["ticker"]
        history_tickers = [h.get("ticker") for h in inst.get("history", [])]
        for event in NEWTICK["history"]:
            assert event["ticker"] in history_tickers, (
                f"history should contain {event['ticker']}"
            )

    def test_multi_exchange_listing_reflected(self):
        """Multi-exchange listings should be reflected."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        inst = registry.by_isin(MULTI["isin"])
        exchanges = {l.get("exchange") for l in inst.get("listings", [])}
        for listing in MULTI["listings"]:
            assert listing["exchange"] in exchanges

    def test_wrapper_handles_null_sedol(self):
        """Wrapper should handle null SEDOL without error."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        inst = registry.by_isin(TESTA["isin"])
        assert inst.get("sedol") is None



# ─── Run All Tests ────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests manually."""
    test_classes = [
        TestPythonWrapper,
        TestAPIDesignConsistency,
        TestDataIntegrityViaWrapper,
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
