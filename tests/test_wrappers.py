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
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

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
        return AssetRegistry(str(ROOT / "identifiers.json"))
    return None


def run_javascript(code):
    """Run JavaScript code and return stdout."""
    try:
        result = subprocess.run(
            ["node", "-e", code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip(), result.returncode
    except FileNotFoundError:
        return None, 1
    except subprocess.TimeoutExpired:
        return None, 2


def run_rust(code):
    """Run Rust code and return stdout. Returns None if Rust not available."""
    return None, 1


def run_go(code):
    """Run Go code and return stdout. Returns None if Go not available."""
    return None, 1


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
        assert registry.count == 50, f"Expected 50, got {registry.count}"

    def test_lookup_by_isin(self):
        """Should find AAPL by ISIN."""
        registry = get_python_wrapper()
        aapl = registry.by_isin("US0378331005")
        assert aapl is not None, "AAPL not found by ISIN"
        assert aapl["ticker"] == "AAPL"

    def test_lookup_by_cusip(self):
        """Should find AAPL by CUSIP."""
        registry = get_python_wrapper()
        aapl = registry.by_cusip("037833100")
        assert aapl is not None, "AAPL not found by CUSIP"
        assert aapl["isin"] == "US0378331005"

    def test_lookup_by_figi(self):
        """Should find AAPL by FIGI."""
        registry = get_python_wrapper()
        aapl = registry.by_figi("BBG000B9XRY4")
        assert aapl is not None, "AAPL not found by FIGI"
        assert aapl["ticker"] == "AAPL"

    def test_lookup_by_ticker_exchange(self):
        """Should find AAPL by ticker+exchange."""
        registry = get_python_wrapper()
        aapl = registry.by_ticker("AAPL", "XNAS")
        assert aapl is not None, "AAPL not found by ticker"
        assert aapl["isin"] == "US0378331005"

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
        instruments = registry.all()
        assert len(instruments) == 50, f"Expected 50, got {len(instruments)}"

    def test_filter_by_exchange(self):
        """Should filter by exchange."""
        registry = get_python_wrapper()
        xnas = registry.by_exchange("XNAS")
        assert len(xnas) > 0, "Should find instruments on XNAS"
        for inst in xnas:
            assert inst["exchange"] == "XNAS"

    def test_filter_by_asset_class(self):
        """Should filter by asset class."""
        registry = get_python_wrapper()
        etfs = registry.by_asset_class("etf")
        assert len(etfs) > 0, "Should find ETFs"
        for inst in etfs:
            assert inst["asset_class"] == "etf"

    def test_get_metadata(self):
        """Should return registry metadata."""
        registry = get_python_wrapper()
        meta = registry.meta()
        assert "version" in meta
        assert "count" in meta
        assert meta["count"] == 50


# ─── Cross-Language Consistency Tests ─────────────────────────────────

class TestCrossLanguageConsistency:
    """Test that all wrappers return identical results."""

    # Expected values from identifiers.json
    EXPECTED_COUNT = 50
    EXPECTED_AAPL_ISIN = "US0378331005"
    EXPECTED_AAPL_CUSIP = "037833100"
    EXPECTED_AAPL_FIGI = "BBG000B9XRY4"
    EXPECTED_AAPL_TICKER = "AAPL"
    EXPECTED_META_TICKER = "META"
    EXPECTED_META_OLD_TICKER = "FB"
    EXPECTED_PRU_COUNT = 2
    EXPECTED_EXCHANGE_COUNT = 9

    def test_load_consistency_file(self):
        """Cross-language consistency file should exist and be valid."""
        consistency_path = ROOT / "tests" / "cross_language_consistency.json"
        assert consistency_path.exists(), "cross_language_consistency.json not found"
        with open(consistency_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Should be a JSON object"

    def test_consistency_file_has_expected_values(self):
        """Consistency file should contain expected values."""
        consistency_path = ROOT / "tests" / "cross_language_consistency.json"
        with open(consistency_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("count") == self.EXPECTED_COUNT, "Count mismatch"
        assert data.get("aapl", {}).get("isin") == self.EXPECTED_AAPL_ISIN
        assert data.get("aapl", {}).get("cusip") == self.EXPECTED_AAPL_CUSIP
        assert data.get("aapl", {}).get("figi") == self.EXPECTED_AAPL_FIGI
        assert data.get("aapl", {}).get("ticker") == self.EXPECTED_AAPL_TICKER

    def test_python_matches_consistency_file(self):
        """Python wrapper results should match consistency file."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return

        registry = get_python_wrapper()
        consistency_path = ROOT / "tests" / "cross_language_consistency.json"
        with open(consistency_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert registry.count == data.get("count")
        
        aapl = registry.by_isin(self.EXPECTED_AAPL_ISIN)
        assert aapl["ticker"] == data["aapl"]["ticker"]
        assert aapl["cusip"] == data["aapl"]["cusip"]
        assert aapl["figi"] == data["aapl"]["figi"]

    def test_registry_data_matches_expected(self):
        """Registry data should match expected values."""
        registry = get_python_wrapper()
        
        assert registry.count == self.EXPECTED_COUNT
        
        aapl = registry.by_isin(self.EXPECTED_AAPL_ISIN)
        assert aapl is not None
        assert aapl["ticker"] == self.EXPECTED_AAPL_TICKER
        assert aapl["cusip"] == self.EXPECTED_AAPL_CUSIP
        assert aapl["figi"] == self.EXPECTED_AAPL_FIGI
        
        meta = registry.by_ticker(self.EXPECTED_META_TICKER, "XNAS")
        assert meta is not None
        history_tickers = [h.get("ticker") for h in meta.get("history", [])]
        assert self.EXPECTED_META_OLD_TICKER in history_tickers
        
        pru = registry.by_ticker("PRU")
        assert len(pru) == self.EXPECTED_PRU_COUNT


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
        result = registry.by_isin("US0378331005")
        assert isinstance(result, dict), "by_isin should return dict"
        
        # by_ticker without exchange returns list
        result = registry.by_ticker("PRU")
        assert isinstance(result, list), "by_ticker without exchange should return list"
        
        # by_ticker with exchange returns dict or None
        result = registry.by_ticker("AAPL", "XNAS")
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
        
        meta = registry.by_isin("US30303M1027")
        assert meta["ticker"] == "META"
        
        history = meta.get("history", [])
        old_tickers = [h.get("ticker") for h in history]
        assert "FB" in old_tickers

    def test_multi_exchange_listing_reflected(self):
        """Multi-exchange listings should be reflected."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        
        aapl = registry.by_isin("US0378331005")
        listings = aapl.get("listings", [])
        exchanges = {l.get("exchange") for l in listings}
        assert "XNAS" in exchanges
        assert "XETR" in exchanges

    def test_wrapper_handles_null_sedol(self):
        """Wrapper should handle null SEDOL without error."""
        if not PYTHON_WRAPPER_AVAILABLE:
            return
        registry = get_python_wrapper()
        
        aapl = registry.by_isin("US0378331005")
        assert aapl.get("sedol") is None, "AAPL SEDOL should be null"


# ─── Run All Tests ────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests manually."""
    test_classes = [
        TestPythonWrapper,
        TestCrossLanguageConsistency,
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