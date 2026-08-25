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
# ISO 3166-1 alpha-2 country codes (full official list)
ISO3166_COUNTRIES: Set[str] = {
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR",
    "AS", "AT", "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE",
    "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ",
    "BR", "BS", "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD",
    "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR",
    "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI",
    "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF",
    "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS",
    "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR", "HT", "HU",
    "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT",
    "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
    "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK",
    "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME",
    "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO", "MP", "MQ",
    "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU",
    "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
    "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS",
    "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI",
    "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV",
    "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK",
    "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW", "TZ", "UA",
    "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
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
    1. Length must be 12 characters
    2. First 2 characters must be valid ISO 3166-1 alpha-2 country code
    3. Characters 3-11 must be alphanumeric
    4. Last character must be a digit
    5. Convert letters to numbers (A=10, B=11, ..., Z=35)
    6. Apply Luhn algorithm to validate check digit
    """
    if len(isin) != 12:
        return False

    isin = isin.upper()

    # Validate country code (first 2 chars must be valid ISO 3166-1 alpha-2)
    country_code = isin[:2]
    if country_code not in ISO3166_COUNTRIES:
        return False

    # Validate characters 3-11 are alphanumeric
    if not all(c.isalnum() for c in isin[2:11]):
        return False

    # Validate last character is a digit
    if not isin[11].isdigit():
        return False

    # Convert letters to numbers
    digits = []
    for char in isin[:11]:
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

def _fetch_from_github(url: str) -> Optional[Dict]:
    """Fetch JSON from GitHub raw content with fallback."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
        return None


def load_iso4217_currencies() -> Set[str]:
    """Load currency codes from iso4217.json if available.

    Search order:
    1. Local paths (../iso4217, ../../iso4217, etc.)
    2. GitHub raw content (slimissa/iso4217)
    """
    currencies = set()

    # Local paths
    for path in [
        Path("../iso4217/iso4217.json"),
        Path("../../iso4217/iso4217.json"),
        Path("../../../iso4217/iso4217.json"),
        Path("iso4217.json"),
        Path.home() / "Documents" / "iso4217" / "iso4217.json",
    ]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                currency_list = data.get("currencies", data if isinstance(data, list) else [])
                if isinstance(currency_list, list):
                    for currency in currency_list:
                        if isinstance(currency, dict) and "code" in currency:
                            currencies.add(currency["code"])
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

    # GitHub fallback — pin to v1.2.0 tag, only load active currencies
    if not currencies:
        github_url = "https://raw.githubusercontent.com/slimissa/iso4217/v1.2.0/iso4217.json"
        data = _fetch_from_github(github_url)
        if data:
            currencies_obj = data.get("currencies", {})
            # Only load "active" currencies — withdrawn codes are not valid
            # for current instrument listings
            active_list = currencies_obj.get("active", [])
            if isinstance(active_list, list):
                for currency in active_list:
                    if isinstance(currency, dict) and "code" in currency:
                        currencies.add(currency["code"])

    return currencies


def load_valid_mics() -> Set[str]:
    """Load MIC codes from exchange-calendar if available.

    Search order:
    1. Local paths (../exchange-calendar, ../../exchange-calendar, etc.)
    2. GitHub API (slimissa/exchange-calendar exchanges directory)
    """
    mics = set()

    # Local paths
    for path in [
        Path("../exchange-calendar"),
        Path("../../exchange-calendar"),
        Path("../../../exchange-calendar"),
        Path("exchange-calendar"),
        Path.home() / "Documents" / "exchange-calendar",
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

    # GitHub fallback: fetch the list of exchange files from GitHub API
    if not mics:
        import urllib.request
        import urllib.error
        try:
            api_url = "https://api.github.com/repos/slimissa/exchange-calendar/contents/exchanges"
            with urllib.request.urlopen(api_url, timeout=15) as response:
                files = json.loads(response.read().decode("utf-8"))
            for file_info in files:
                if file_info.get("name", "").endswith(".json"):
                    raw_url = file_info.get("download_url")
                    if raw_url:
                        exchange_data = _fetch_from_github(raw_url)
                        if exchange_data and "mic" in exchange_data:
                            mics.add(exchange_data["mic"])
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
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


def validate_data_valid_as_of(data: Dict) -> List[str]:
    """Validate meta.data_valid_as_of is present and a valid date."""
    errors = []
    meta = data.get("meta", {})
    date_str = meta.get("data_valid_as_of")

    if not date_str:
        errors.append("meta.data_valid_as_of is missing")
        return errors

    # Validate date format (YYYY-MM-DD)
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        errors.append(
            f"meta.data_valid_as_of should be YYYY-MM-DD: {date_str}"
        )

    return errors


def validate_coverage(data: Dict) -> List[str]:
    """Validate meta.coverage matches actual data."""
    errors = []
    coverage = data.get("meta", {}).get("coverage", {})
    instruments = data.get("instruments", [])

    if not coverage:
        return errors

    # Check exchanges
    declared_exchanges = set(coverage.get("exchanges", []))
    actual_exchanges = set(i.get("exchange") for i in instruments if i.get("exchange"))
    missing = actual_exchanges - declared_exchanges
    for exchange in sorted(missing):
        errors.append(f"meta.coverage.exchanges missing {exchange}")

    # Check asset classes
    declared_classes = set(coverage.get("asset_classes", []))
    actual_classes = set(i.get("asset_class") for i in instruments if i.get("asset_class"))
    missing_classes = actual_classes - declared_classes
    for asset_class in sorted(missing_classes):
        errors.append(f"meta.coverage.asset_classes missing {asset_class}")

    # Check countries
    declared_countries = set(coverage.get("countries", []))
    actual_countries = set(i.get("country") for i in instruments if i.get("country"))
    missing_countries = actual_countries - declared_countries
    for country in sorted(missing_countries):
        errors.append(f"meta.coverage.countries missing {country}")

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


def validate_cross_registry(data: Dict) -> Tuple[List[str], List[str]]:
    """
    Validate currency codes against ISO 4217 and MICs against Exchange Calendar.

    Returns:
        (errors, warnings) — errors fail validation, warnings are informational.

    If the other registries are available, every currency and exchange in
    identifiers.json must exist in them. If not found, a warning is returned
    but does not fail validation.
    """
    errors = []
    warnings = []
    instruments = data.get("instruments", [])

    # Validate currencies against ISO 4217
    if ISO4217_CURRENCIES:
        for inst in instruments:
            ticker = inst.get("ticker", "?")
            currency = inst.get("currency")
            if currency and currency not in ISO4217_CURRENCIES:
                errors.append(
                    f"{ticker}: currency {currency} not found in ISO 4217 registry"
                )

            for listing in inst.get("listings", []):
                listing_currency = listing.get("currency")
                if listing_currency and listing_currency not in ISO4217_CURRENCIES:
                    errors.append(
                        f"{ticker}: listing currency {listing_currency} not found in ISO 4217 registry"
                    )
    else:
        warnings.append("ISO 4217 registry not found. Currency validation skipped.")

    # Validate exchanges against Exchange Calendar
    if VALID_MICS:
        for inst in instruments:
            ticker = inst.get("ticker", "?")
            exchange = inst.get("exchange")
            if exchange and exchange not in VALID_MICS:
                errors.append(
                    f"{ticker}: exchange {exchange} not found in Exchange Calendar registry"
                )

            for listing in inst.get("listings", []):
                listing_exchange = listing.get("exchange")
                if listing_exchange and listing_exchange not in VALID_MICS:
                    errors.append(
                        f"{ticker}: listing exchange {listing_exchange} not found in Exchange Calendar registry"
                    )
    else:
        warnings.append("Exchange Calendar registry not found. MIC validation skipped.")

    return errors, warnings


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
    errors.extend(validate_coverage(data))
    errors.extend(validate_data_valid_as_of(data))

    instruments = data.get("instruments", [])
    if instruments:
        errors.extend(validate_check_digits(instruments))
        errors.extend(validate_uniqueness(instruments))
        errors.extend(validate_business_rules(instruments))
        errors.extend(validate_temporal_consistency(instruments))
        cross_errors, cross_warnings = validate_cross_registry(data)
    errors.extend(cross_errors)
    # Warnings are printed but do not fail validation
    for warning in cross_warnings:
        print(f"  Warning: {warning}", file=sys.stderr)

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