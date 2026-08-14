#!/usr/bin/env python3
"""
Check-digit algorithm tests for ISIN, CUSIP, and SEDOL.

Tests cover:
- Valid check digits (known-correct values from official sources)
- Invalid check digits (wrong digit, wrong length, wrong format)
- Edge cases (letters in wrong positions, vowels in SEDOL, boundary values)
- Round-trip consistency (known ISIN → CUSIP mapping)
- Real-world instruments from the registry

Run:
    python3 tests/test_check_digits.py
    python3 -m pytest tests/test_check_digits.py -v
"""

import sys
import json
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from validate import (
    validate_isin_check_digit,
    validate_cusip_check_digit,
    validate_sedol_check_digit,
)


# ─── ISIN Tests ───────────────────────────────────────────────────────

class TestISINCheckDigit:
    """ISIN check-digit validation (ISO 6166)."""

    def test_valid_us_isins(self):
        """Known-valid US ISINs."""
        valid_isins = [
            "US0378331005",  # Apple Inc.
            "US5949181045",  # Microsoft Corporation
            "US0231351067",  # Amazon.com, Inc.
            "US30303M1027",  # Meta Platforms, Inc.
            "US67066G1040",  # NVIDIA Corporation
            "US88160R1014",  # Tesla, Inc.
            "US78462F1030",  # SPDR S&P 500 ETF
            "US46090E1038",  # Invesco QQQ Trust
            "US46625H1005",  # JPMorgan Chase & Co.
            "US4781601046",  # Johnson & Johnson
        ]
        for isin in valid_isins:
            assert validate_isin_check_digit(isin), f"Should be valid: {isin}"

    def test_valid_international_isins(self):
        """Known-valid international ISINs."""
        valid_isins = [
            "GB0007099541",  # Prudential plc (London)
            "JP3435000009",  # Sony Group Corporation
            "DE0007164600",  # SAP SE
            "FR0000121014",  # LVMH
            "CH0012032048",  # Roche Holding AG
            "HK0941009539",  # Tencent Holdings
            "KR7005930003",  # Samsung Electronics
        ]
        for isin in valid_isins:
            assert validate_isin_check_digit(isin), f"Should be valid: {isin}"

    def test_invalid_check_digit(self):
        """Wrong check digit should fail."""
        invalid_isins = [
            "US0378331000",  # Apple with wrong check digit (0 instead of 5)
            "US5949181040",  # Microsoft with wrong check digit
            "US0231351060",  # Amazon with wrong check digit
            "GB0007099540",  # Prudential with wrong check digit
            "JP3435000000",  # Sony with wrong check digit
        ]
        for isin in invalid_isins:
            assert not validate_isin_check_digit(isin), f"Should be invalid: {isin}"

    def test_invalid_length(self):
        """Wrong length should fail."""
        invalid_lengths = [
            "US037833100",      # 11 chars (too short)
            "US03783310050",    # 13 chars (too long)
            "US03783310",       # 10 chars
            "US037833100500",   # 14 chars
            "",                  # empty
            "US",                # 2 chars
        ]
        for isin in invalid_lengths:
            assert not validate_isin_check_digit(isin), f"Should be invalid length: {isin}"

    def test_invalid_country_code(self):
        """Invalid country codes should fail."""
        invalid_countries = [
            "XX0378331005",  # XX is not a valid ISO 3166-1 alpha-2 code
            "ZZ0378331005",  # ZZ is not assigned
            "1A0378331005",  # digit in country code
            "U50378331005",  # digit in country code
        ]
        for isin in invalid_countries:
            assert not validate_isin_check_digit(isin), f"Should be invalid country: {isin}"

    def test_invalid_characters(self):
        """Non-alphanumeric characters should fail."""
        invalid_chars = [
            "US037833100!",  # ! not allowed
            "US037833100 ",  # space not allowed
            "US037833100-",  # - not allowed
            "US037833100.",  # . not allowed
        ]
        for isin in invalid_chars:
            assert not validate_isin_check_digit(isin), f"Should be invalid char: {isin}"

    def test_case_insensitivity(self):
        """Lowercase ISINs should validate correctly."""
        assert validate_isin_check_digit("us0378331005")  # Apple lowercase
        assert validate_isin_check_digit("gb0007099541")  # Prudential lowercase

    def test_luhn_algorithm_specific(self):
        """Specific Luhn algorithm test cases."""
        # Known Luhn test values
        assert validate_isin_check_digit("US0000000000") == False  # All zeros
        assert validate_isin_check_digit("US9999999999") == False  # All nines

    def test_real_registry_isins(self):
        """Every ISIN in the actual registry should validate."""
        registry_path = Path(__file__).parent.parent / "identifiers.json"
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for instrument in data.get("instruments", []):
                isin = instrument.get("isin")
                if isin:
                    assert validate_isin_check_digit(isin), (
                        f"Registry ISIN failed validation: {isin} "
                        f"(ticker: {instrument.get('ticker', '?')})"
                    )


# ─── CUSIP Tests ──────────────────────────────────────────────────────

class TestCUSIPCheckDigit:
    """CUSIP check-digit validation (modified Luhn)."""

    def test_valid_cusips(self):
        """Known-valid CUSIPs."""
        valid_cusips = [
            "037833100",  # Apple Inc.
            "594918104",  # Microsoft Corporation
            "023135106",  # Amazon.com, Inc.
            "30303M102",  # Meta Platforms, Inc.
            "67066G104",  # NVIDIA Corporation
            "88160R101",  # Tesla, Inc.
            "78462F103",  # SPDR S&P 500 ETF
            "46090E103",  # Invesco QQQ Trust
            "46625H100",  # JPMorgan Chase & Co.
            "478160104",  # Johnson & Johnson
        ]
        for cusip in valid_cusips:
            assert validate_cusip_check_digit(cusip), f"Should be valid: {cusip}"

    def test_invalid_check_digit(self):
        """Wrong check digit should fail."""
        invalid_cusips = [
            "037833101",  # Apple with wrong check digit
            "594918105",  # Microsoft with wrong check digit
            "023135107",  # Amazon with wrong check digit
            "30303M103",  # Meta with wrong check digit
        ]
        for cusip in invalid_cusips:
            assert not validate_cusip_check_digit(cusip), f"Should be invalid: {cusip}"

    def test_invalid_length(self):
        """Wrong length should fail."""
        invalid_lengths = [
            "03783310",    # 8 chars (too short)
            "0378331000",  # 10 chars (too long)
            "0378331",     # 7 chars
            "",             # empty
        ]
        for cusip in invalid_lengths:
            assert not validate_cusip_check_digit(cusip), f"Should be invalid length: {cusip}"

    def test_letters_in_positions(self):
        """Letters are valid in CUSIP positions 1-8."""
        assert validate_cusip_check_digit("30303M102")  # Meta (letter M in position 6)
        assert validate_cusip_check_digit("67066G104")  # NVIDIA (letter G)

    def test_case_insensitivity(self):
        """Lowercase CUSIPs should validate."""
        assert validate_cusip_check_digit("037833100")  # Apple
        assert validate_cusip_check_digit("30303m102")  # Meta lowercase

    def test_real_registry_cusips(self):
        """Every CUSIP in the actual registry should validate."""
        registry_path = Path(__file__).parent.parent / "identifiers.json"
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for instrument in data.get("instruments", []):
                cusip = instrument.get("cusip")
                if cusip:
                    assert validate_cusip_check_digit(cusip), (
                        f"Registry CUSIP failed validation: {cusip} "
                        f"(ticker: {instrument.get('ticker', '?')})"
                    )


# ─── SEDOL Tests ──────────────────────────────────────────────────────

class TestSEDOLCheckDigit:
    """SEDOL check-digit validation (weighted sum)."""

    def test_valid_sedols(self):
        """Known-valid SEDOLs."""
        valid_sedols = [
            "2046251",  # Apple Inc.
            "B0WNLY7",  # Valid example (from SEDOL spec)
            "0709954",  # Prudential plc
            "7123870",  # Roche Holding AG
        ]
        for sedol in valid_sedols:
            assert validate_sedol_check_digit(sedol), f"Should be valid: {sedol}"

    def test_invalid_check_digit(self):
        """Wrong check digit should fail."""
        invalid_sedols = [
            "2046250",  # Apple with wrong check digit
            "B0WNLY6",  # Wrong check digit
            "0709953",  # Prudential with wrong check digit
        ]
        for sedol in invalid_sedols:
            assert not validate_sedol_check_digit(sedol), f"Should be invalid: {sedol}"

    def test_vowels_not_allowed(self):
        """SEDOLs cannot contain vowels in first 6 characters."""
        invalid_vowels = [
            "A0WNLY7",  # A is a vowel
            "E0WNLY7",  # E is a vowel
            "I0WNLY7",  # I is a vowel
            "O0WNLY7",  # O is a vowel
            "U0WNLY7",  # U is a vowel
        ]
        for sedol in invalid_vowels:
            assert not validate_sedol_check_digit(sedol), f"Should reject vowel: {sedol}"

    def test_invalid_length(self):
        """Wrong length should fail."""
        invalid_lengths = [
            "204625",   # 6 chars (too short)
            "20462510", # 8 chars (too long)
            "20462",    # 5 chars
            "",          # empty
        ]
        for sedol in invalid_lengths:
            assert not validate_sedol_check_digit(sedol), f"Should be invalid length: {sedol}"

    def test_case_insensitivity(self):
        """Lowercase SEDOLs should validate."""
        assert validate_sedol_check_digit("2046251")  # Apple
        assert validate_sedol_check_digit("b0wnly7")  # Lowercase

    def test_weighted_sum_algorithm(self):
        """Specific weighted sum test cases."""
        # Manual calculation for 2046251:
        # 2*1 + 0*3 + 4*1 + 6*7 + 2*3 + 5*9 = 2 + 0 + 4 + 42 + 6 + 45 = 99
        # Check: (10 - (99 % 10)) % 10 = (10 - 9) % 10 = 1
        assert validate_sedol_check_digit("2046251")


# ─── Cross-Algorithm Tests ────────────────────────────────────────────

class TestCrossAlgorithm:
    """Cross-validation between different identifier types."""

    def test_isin_contains_cusip_for_us(self):
        """US ISIN should contain the CUSIP as part of the ISIN."""
        # Apple: ISIN US0378331005 → CUSIP 037833100
        # The US ISIN format is: US + CUSIP + check digit
        isin = "US0378331005"
        cusip = "037833100"
        assert isin[2:11] == cusip, "US ISIN should contain CUSIP"

    def test_registry_isin_cusip_consistency(self):
        """Every US instrument in the registry should have ISIN containing CUSIP."""
        registry_path = Path(__file__).parent.parent / "identifiers.json"
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for instrument in data.get("instruments", []):
                isin = instrument.get("isin")
                cusip = instrument.get("cusip")
                if isin and cusip and isin.startswith("US"):
                    assert isin[2:11] == cusip, (
                        f"ISIN-CUSIP mismatch for {instrument.get('ticker', '?')}: "
                        f"ISIN {isin} should contain CUSIP {cusip}"
                    )


# ─── Main Test Runner ─────────────────────────────────────────────────

def run_all_tests():
    """Run all tests manually (without pytest)."""
    tests = []
    
    # Collect all test methods
    for cls in [TestISINCheckDigit, TestCUSIPCheckDigit, TestSEDOLCheckDigit, TestCrossAlgorithm]:
        for method_name in dir(cls):
            if method_name.startswith("test_"):
                method = getattr(cls(), method_name)
                tests.append((f"{cls.__name__}.{method_name}", method))
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"  PASS: {test_name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {test_name}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test_name}: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)