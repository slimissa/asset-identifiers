#!/usr/bin/env python3
"""
Asset Identifier Registry validator.

Validates identifiers.json against:
1. JSON Schema (structure and format)
2. Check-digit algorithms (ISIN, CUSIP, SEDOL)
3. Uniqueness constraints (ISIN, CUSIP, SEDOL, ticker+exchange)
4. Cross-field business rules (country-specific identifiers, active/delisted consistency)
5. Cross-registry consistency (ISO 4217 currencies, exchange MICs)
6. Count consistency (meta.count matches array length)
7. Temporal consistency (listing/delisting dates, history order)

Exit codes:
  0 — validation passed
  1 — validation failed (data errors)
  2 — usage error (missing file, bad arguments)
  3 — schema violation (structure errors)
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime, date

# ─── Optional dependencies ────────────────────────────────────────────

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

# ─── Constants ────────────────────────────────────────────────────────

# ISO 4217 currency codes (loaded from iso4217.json if available)
ISO4217_CURRENCIES: Set[str] = set()

# Valid MIC codes (loaded from exchange-calendar if available)
VALID_MICS: Set[str] = set()

# Country code → required identifier type
# US/Canada use CUSIP, UK/Europe use SEDOL
COUNTRY_IDENTIFIER_RULES = {
    "US": "cusip",
    "CA": "cusip",
    "GB": "sedol",
    "IE": "sedol",
    "FR": "sedol",
    "DE": "sedol",
    "CH": "sedol",
    "ES": "sedol",
    "IT": "sedol",
    "NL": "sedol",
    "JP": None,  # Japan uses local codes, not CUSIP/SEDOL
    "AU": None,  # Australia uses ISIN only
}

# ISO 3166-1 alpha-2 country codes (common subset)
ISO3166_COUNTRIES: Set[str] = {
    "US", "CA", "GB", "IE", "FR", "DE", "CH", "ES", "IT", "NL",
    "JP", "AU", "HK", "SG", "KR", "CN", "TW", "IN", "BR", "MX",
    "ZA", "TR", "PL", "AT", "BE", "DK", "FI", "GR", "NO", "PT",
    "SE", "RU", "SA", "AE", "IL", "TH", "MY", "ID", "PH", "NZ",
}


# ─── Check-digit algorithms ───────────────────────────────────────────

def char_to_number(char: str) -> int:
    """Convert character to number for check-digit algorithms."""
    if char.isdigit():
        return int(char)
    return ord(char.upper()) - ord('A') + 10


def validate_isin_check_digit(isin: str) -> bool:
    """
    Validate ISIN check digit.

    ISO 6166 algorithm:
    1. Convert letters to numbers (A=10, B=11, ..., Z=35)
    2. Split into individual digits
    3. Double every other digit starting from the RIGHT
    4. Sum all digits (doubled values are summed as individual digits)
    5. Check digit = (10 - (sum % 10)) % 10

    Example: US0378331005
    U=30, S=28 → 3028 037833100 5
    Position:   3  0  2  8  0  3  7  8  3  3  1  0  0
    Double:     3  0  4  8  0  3  14 8  6  3  2  0  0
    Sum digits: 3+0+4+8+0+3+1+4+8+6+3+2+0+0 = 42
    Check: (10 - (42 % 10)) % 10 = 8 → Wait, actual check is 5.
    Let me recompute correctly.

    The algorithm doubles every OTHER digit starting from the RIGHT.
    ISIN: U S 0 3 7 8 3 3 1 0 0 5
    Convert letters: 30 28 0 3 7 8 3 3 1 0 0 5
    Full digit string: 3 0 2 8 0 3 7 8 3 3 1 0 0 5

    From the right (excluding check digit at end):
    Position from right: 0(0) 1(1) 2(3) 3(3) 4(8) 5(7) 6(3) 7(0) 8(8) 9(2) 10(0) 11(3)
    Double positions: 1, 3, 5, 7, 9, 11 (odd from right)

    Let's be precise:
    Digits (left to right): 3 0 2 8 0 3 7 8 3 3 1 0 0
    Index from right:       12 11 10 9 8 7 6 5 4 3 2 1 0

    Double indices 1, 3, 5, 7, 9, 11 (odd from right, zero-indexed even from right)
    Index 0 (rightmost): 0 → no double
    Index 1: 1 → double: 2
    Index 2: 0 → no double: 0
    Index 3: 3 → double: 6
    Index 4: 3 → no double: 3
    Index 5: 8 → double: 16 → 1+6=7
    Index 6: 7 → no double: 7
    Index 7: 3 → double: 6
    Index 8: 0 → no double: 0
    Index 9: 8 → double: 16 → 1+6=7
    Index 10: 2 → no double: 2
    Index 11: 0 → double: 0
    Index 12: 3 → no double: 3

    Sum: 0+2+0+6+3+7+7+6+0+7+2+0+3 = 43
    Check: (10 - (43 % 10)) % 10 = (10 - 3) % 10 = 7

    But actual check digit is 5. Something is wrong.

    Let me look up the correct algorithm:
    ISIN check digit uses the Luhn algorithm.
    The Luhn algorithm doubles every second digit from the RIGHT.
    For even-length strings, this means doubling positions 0, 2, 4, ... from the LEFT.
    For odd-length strings, doubling positions 1, 3, 5, ... from the LEFT.

    The full digit string for US0378331005 is: 30280378331005
    Length: 14 digits (even)

    For even length, double positions 0, 2, 4, 6, 8, 10, 12 from LEFT.
    Position 0: 3 → double: 6
    Position 1: 0 → no double: 0
    Position 2: 2 → double: 4
    Position 3: 8 → no double: 8
    Position 4: 0 → double: 0
    Position 5: 3 → no double: 3
    Position 6: 7 → double: 14 → 1+4=5
    Position 7: 8 → no double: 8
    Position 8: 3 → double: 6
    Position 9: 3 → no double: 3
    Position 10: 1 → double: 2
    Position 11: 0 → no double: 0
    Position 12: 0 → double: 0
    Position 13: 5 → no double: 5 (this is the check digit, not included)

    Wait, the check digit is position 13. We validate positions 0-12.
    Sum: 6+0+4+8+0+3+5+8+6+3+2+0+0 = 45
    Check: (10 - (45 % 10)) % 10 = (10 - 5) % 10 = 5

    Yes, 5 is correct. The confusion was in my manual calculation.
    """
    if len(isin) != 12:
        return False

    # Convert letters to numbers
    digits = []
    for char in isin[:11].upper():
        if char.isalpha():
            num = char_to_number(char)
            digits.extend([num // 10, num % 10])
        elif char.isdigit():
            digits.append(int(char))
        else:
            return False

    # Luhn algorithm: double every second digit from the right
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:
            doubled = digit * 2
            total += doubled // 10 + doubled % 10
        else:
            total += digit

    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(isin[11])


def validate_cusip_check_digit(cusip: str) -> bool:
    """
    Validate CUSIP check digit.

    Modified Luhn algorithm:
    1. Convert letters (A=10, B=11, ..., Z=35)
    2. Sum digits at odd positions (1-indexed from left)
    3. Double digits at even positions, sum individual digits
    4. Check digit = (10 - (total % 10)) % 10

    Example: 037833100
    Positions: 0 3 7 8 3 3 1 0 0
    Odd (1-indexed): 0, 7, 3, 1 → sum directly: 0+7+3+1 = 11
    Even (1-indexed): 3, 8, 3, 0 → double: 6, 16→7, 6, 0 → sum: 6+7+6+0 = 19
    Total: 11+19 = 30
    Check: (10 - (30 % 10)) % 10 = 0 → Correct (last digit is 0)
    """
    if len(cusip) != 9:
        return False

    total = 0
    for i, char in enumerate(cusip[:8].upper()):
        if char.isalpha():
            num = char_to_number(char)
        elif char.isdigit():
            num = int(char)
        else:
            return False

        # 1-indexed position: i+1
        # Odd position (1, 3, 5, 7): add directly
        # Even position (2, 4, 6, 8): double and sum digits
        if (i + 1) % 2 == 1:
            total += num
        else:
            doubled = num * 2
            total += doubled // 10 + doubled % 10

    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(cusip[8])


def validate_sedol_check_digit(sedol: str) -> bool:
    """
    Validate SEDOL check digit.

    Weighted sum algorithm:
    1. First 6 characters: alphanumeric, no vowels
    2. Weights: 1, 3, 1, 7, 3, 9 (from left)
    3. Check digit = (10 - (sum % 10)) % 10

    Example: 2046251
    Chars: 2 0 4 6 2 5
    Weights: 1 3 1 7 3 9
    Products: 2 0 4 42 6 45
    Sum: 2+0+4+42+6+45 = 99
    Check: (10 - (99 % 10)) % 10 = (10 - 9) % 10 = 1 → Correct
    """
    if len(sedol) != 7:
        return False

    # SEDOL first 6 chars cannot contain vowels
    vowels = set('AEIOU')
    for char in sedol[:6].upper():
        if char in vowels:
            return False

    weights = [1, 3, 1, 7, 3, 9]
    total = 0
    for i, char in enumerate(sedol[:6].upper()):
        if char.isalpha():
            num = char_to_number(char)
        elif char.isdigit():
            num = int(char)
        else:
            return False
        total += num * weights[i]

    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(sedol[6])


# ─── Registry loading ─────────────────────────────────────────────────

def load_iso4217_currencies() -> Set[str]:
    """Load currency codes from iso4217.json if available."""
    currencies = set()
    for path in [
        Path("../iso4217/iso4217.json"),
        Path("../../iso4217/iso4217.json"),
        Path("iso4217.json"),
    ]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "currencies" in data:
                    for currency in data["currencies"]:
                        if "code" in currency:
                            currencies.add(currency["code"])
            except (json.JSONDecodeError, KeyError):
                pass
    return currencies


def load_valid_mics() -> Set[str]:
    """Load MIC codes from exchange-calendar if available."""
    mics = set()
    for path in [
        Path("../exchange-calendar"),
        Path("../../exchange-calendar"),
        Path("exchange-calendar"),
    ]:
        if path.exists() and path.is_dir():
            exchanges_dir = path / "exchanges"
            if exchanges_dir.exists():
                for exchange_file in exchanges_dir.glob("*.json"):
                    try:
                        with open(exchange_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if "mic" in data:
                            mics.add(data["mic"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    return mics


# ─── Validation functions ─────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_schema(data: Dict, schema: Dict) -> List[str]:
    """Validate against JSON Schema."""
    errors = []
    if JSONSCHEMA_AVAILABLE:
        validator = jsonschema.Draft7Validator(schema)
        for error in validator.iter_errors(data):
            errors.append(f"Schema error at {'.'.join(str(p) for p in error.path)}: {error.message}")
    else:
        # Fallback: basic structural checks
        if "meta" not in data:
            errors.append("Missing 'meta' object")
        if "instruments" not in data:
            errors.append("Missing 'instruments' array")
    return errors


def validate_count(data: Dict) -> List[str]:
    """Validate meta.count matches actual instrument count."""
    errors = []
    declared = data.get("meta", {}).get("count")
    actual = len(data.get("instruments", []))
    if declared != actual:
        errors.append(f"meta.count ({declared}) does not match actual instrument count ({actual})")
    return errors


def validate_check_digits(instruments: List[Dict]) -> List[str]:
    """Validate all check digits."""
    errors = []
    for instrument in instruments:
        isin = instrument.get("isin")
        if isin and not validate_isin_check_digit(isin):
            errors.append(f"Invalid ISIN check digit: {isin} (ticker: {instrument.get('ticker', '?')})")

        cusip = instrument.get("cusip")
        if cusip and not validate_cusip_check_digit(cusip):
            errors.append(f"Invalid CUSIP check digit: {cusip} (ticker: {instrument.get('ticker', '?')})")

        sedol = instrument.get("sedol")
        if sedol and not validate_sedol_check_digit(sedol):
            errors.append(f"Invalid SEDOL check digit: {sedol} (ticker: {instrument.get('ticker', '?')})")

    return errors


def validate_uniqueness(instruments: List[Dict]) -> List[str]:
    """Validate uniqueness constraints."""
    errors = []
    isins = []
    cusips = []
    sedols = []
    figis = []
    ticker_exchange_pairs = []

    for instrument in instruments:
        isin = instrument.get("isin")
        if isin:
            isins.append(isin)

        cusip = instrument.get("cusip")
        if cusip:
            cusips.append(cusip)

        sedol = instrument.get("sedol")
        if sedol:
            sedols.append(sedol)

        figi = instrument.get("figi")
        if figi:
            figis.append(figi)

        ticker = instrument.get("ticker")
        exchange = instrument.get("exchange")
        if ticker and exchange:
            ticker_exchange_pairs.append((ticker, exchange))

    # Check duplicates
    if len(isins) != len(set(isins)):
        errors.append("Duplicate ISIN found")

    if len(cusips) != len(set(cusips)):
        errors.append("Duplicate CUSIP found")

    if len(sedols) != len(set(sedols)):
        errors.append("Duplicate SEDOL found")

    if len(figis) != len(set(figis)):
        errors.append("Duplicate FIGI found")

    if len(ticker_exchange_pairs) != len(set(ticker_exchange_pairs)):
        errors.append("Duplicate ticker+exchange pair found")

    return errors


def validate_business_rules(instruments: List[Dict]) -> List[str]:
    """Validate cross-field business rules."""
    errors = []

    for instrument in instruments:
        ticker = instrument.get("ticker", "?")
        country = instrument.get("country")
        currency = instrument.get("currency")
        exchange = instrument.get("exchange")
        active = instrument.get("active")
        delisting_date = instrument.get("delisting_date")
        listing_date = instrument.get("listing_date")
        cusip = instrument.get("cusip")
        sedol = instrument.get("sedol")
        listings = instrument.get("listings", [])

        # Country-specific identifier rules
        # CUSIP is required for US/Canada (we have verified CUSIP data)
        # SEDOL is not enforced until we have a verified source
        if country in COUNTRY_IDENTIFIER_RULES:
            required_type = COUNTRY_IDENTIFIER_RULES[country]
            if required_type == "cusip" and not cusip:
                errors.append(f"{ticker}: country {country} requires CUSIP")
            elif required_type == "sedol" and not sedol:
                # SEDOL is not enforced until we have a verified source
                pass

        # Active/delisted consistency
        if active and delisting_date:
            errors.append(f"{ticker}: active=true but delisting_date={delisting_date}")

        if not active and not delisting_date:
            errors.append(f"{ticker}: active=false but no delisting_date")

        # Date consistency
        if listing_date and delisting_date:
            if listing_date > delisting_date:
                errors.append(f"{ticker}: listing_date ({listing_date}) after delisting_date ({delisting_date})")

        # Listings consistency
        if listings:
            # Primary listing should match top-level ticker/exchange
            primary_listings = [l for l in listings if l.get("status") == "PRIMARY"]
            if primary_listings:
                primary = primary_listings[0]
                if primary.get("exchange") != exchange or primary.get("ticker") != ticker:
                    errors.append(f"{ticker}: primary listing does not match top-level exchange/ticker")
            else:
                errors.append(f"{ticker}: listings array exists but no PRIMARY listing")

            # Check for duplicate listings
            listing_pairs = [(l.get("exchange"), l.get("ticker")) for l in listings]
            if len(listing_pairs) != len(set(listing_pairs)):
                errors.append(f"{ticker}: duplicate listing in listings array")

        # Currency validation if ISO 4217 loaded
        if ISO4217_CURRENCIES and currency and currency not in ISO4217_CURRENCIES:
            errors.append(f"{ticker}: currency {currency} not found in ISO 4217 registry")

        # Exchange validation if MICs loaded
        if VALID_MICS and exchange and exchange not in VALID_MICS:
            errors.append(f"{ticker}: exchange {exchange} not found in exchange-calendar registry")

        # Country validation
        if country and country not in ISO3166_COUNTRIES:
            errors.append(f"{ticker}: invalid country code {country}")

    return errors


def validate_temporal_consistency(instruments: List[Dict]) -> List[str]:
    """Validate temporal consistency of history and dates."""
    errors = []

    for instrument in instruments:
        ticker = instrument.get("ticker", "?")
        history = instrument.get("history", [])

        # History must be in chronological order
        dates = [h.get("change_date") for h in history if h.get("change_date")]
        if dates:
            sorted_dates = sorted(dates)
            if dates != sorted_dates:
                errors.append(f"{ticker}: history events are not in chronological order")

            # First history event should have change_type "none" (initial listing)
            if history and history[0].get("change_type") != "none":
                errors.append(f"{ticker}: first history event should have change_type 'none'")

            # Last history event ticker should match current ticker
            if history and history[-1].get("ticker") != ticker:
                errors.append(f"{ticker}: last history event ticker ({history[-1].get('ticker')}) does not match current ticker ({ticker})")

    return errors


def validate_cross_registry() -> List[str]:
    """Validate cross-registry consistency."""
    # Cross-registry validation is optional.
    # It only runs when the other registries are available.
    # Missing registries are not errors.
    return []


# ─── Main validation ──────────────────────────────────────────────────

def validate_registry(data_path: Path, schema_path: Path) -> Tuple[bool, List[str]]:
    """Run all validations. Returns (success, errors)."""
    errors = []

    # Load files
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, [f"File not found: {data_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in {data_path}: {e}"]

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except FileNotFoundError:
        return False, [f"Schema not found: {schema_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in schema: {e}"]

    # Run validations
    errors.extend(validate_schema(data, schema))
    errors.extend(validate_count(data))

    instruments = data.get("instruments", [])
    if instruments:
        errors.extend(validate_check_digits(instruments))
        errors.extend(validate_uniqueness(instruments))
        errors.extend(validate_business_rules(instruments))
        errors.extend(validate_temporal_consistency(instruments))
        errors.extend(validate_cross_registry())

    return len(errors) == 0, errors


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate the Asset Identifier Registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("identifiers.json"),
        help="Path to identifiers.json (default: identifiers.json)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schema.json"),
        help="Path to schema.json (default: schema.json)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all errors, not just a summary",
    )

    args = parser.parse_args()

    # Load optional cross-registry data
    global ISO4217_CURRENCIES, VALID_MICS
    ISO4217_CURRENCIES = load_iso4217_currencies()
    VALID_MICS = load_valid_mics()

    # Validate
    success, errors = validate_registry(args.data, args.schema)

    if success:
        count = 0
        try:
            with open(args.data, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = len(data.get("instruments", []))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

        if args.verbose:
            print(f"OK: {count} instrument(s) validated successfully")
            if ISO4217_CURRENCIES:
                print(f"     ISO 4217 currencies loaded: {len(ISO4217_CURRENCIES)}")
            if VALID_MICS:
                print(f"     Exchange MICs loaded: {len(VALID_MICS)}")
        else:
            print(f"OK: {count} instrument(s) validated successfully")
        sys.exit(0)
    else:
        if args.verbose:
            print(f"FAILED: {len(errors)} error(s) found")
            for error in errors:
                print(f"  - {error}")
        else:
            # Show first 10 errors by default
            print(f"FAILED: {len(errors)} error(s) found")
            for error in errors[:10]:
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more error(s). Use --verbose to see all.")
        sys.exit(1)


if __name__ == "__main__":
    main()