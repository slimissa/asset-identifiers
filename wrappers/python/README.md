# Asset Identifiers Registry — Python Wrapper

A lightweight, dependency-free Python interface to the canonical asset identifier registry.

## Installation

```bash
pip install asset-identifiers-registry
```

Or install from source:

```bash
git clone https://github.com/slimissa/asset-identifiers.git
cd asset-identifiers/wrappers/python
pip install -e .
```

## Quick Start

```python
from asset_identifiers import AssetRegistry

# Load the registry
registry = AssetRegistry("identifiers.json")

# Get instrument count
print(registry.count)  # 50

# Look up by ISIN
aapl = registry.by_isin("US0378331005")
print(aapl["ticker"])      # AAPL
print(aapl["name"])        # Apple Inc.
print(aapl["currency"])    # USD
print(aapl["exchange"])    # XNAS

# Look up by CUSIP
msft = registry.by_cusip("594918104")
print(msft["ticker"])      # MSFT

# Look up by FIGI
aapl = registry.by_figi("BBG000B9XRY4")
print(aapl["name"])        # Apple Inc.

# Look up by ticker on a specific exchange
aapl = registry.by_ticker("AAPL", "XNAS")
print(aapl["isin"])        # US0378331005

# Look up by ticker without exchange (returns list for ambiguous tickers)
pru_all = registry.by_ticker("PRU")
print(len(pru_all))        # 2 (Prudential plc on XLON, Prudential Financial on XNYS)

# Disambiguate by exchange
pru_london = registry.by_ticker("PRU", "XLON")
print(pru_london["name"])  # Prudential plc

pru_nyse = registry.by_ticker("PRU", "XNYS")
print(pru_nyse["name"])    # Prudential Financial, Inc.

# Filter by exchange
nasdaq_instruments = registry.by_exchange("XNAS")
print(len(nasdaq_instruments))

# Filter by asset class
etfs = registry.by_asset_class("etf")
print(len(etfs))

# Filter by country
us_instruments = registry.by_country("US")
print(len(us_instruments))

# Filter by currency
usd_instruments = registry.by_currency("USD")
print(len(usd_instruments))

# Get all instruments
all_instruments = registry.all()
for inst in all_instruments:
    print(f"{inst['ticker']} ({inst['exchange']}): {inst['isin']}")

# Get registry metadata
meta = registry.meta()
print(meta["version"])     # 1.0.0
print(meta["count"])       # 50
print(meta["generated"])   # 2026-08-14

# Get aggregate information
print(registry.exchanges())      # ['XETR', 'XHKG', ...]
print(registry.asset_classes())  # ['equity', 'etf']
print(registry.currencies())     # ['CHF', 'EUR', ...]
print(registry.countries())      # ['CH', 'DE', ...]

# Check if an identifier exists
print(registry.isin_exists("US0378331005"))   # True
print(registry.ticker_exists("ZZZZ"))          # False

# Auto-detect identifier type with resolve()
result = registry.resolve("US0378331005")     # Detects ISIN
result = registry.resolve("037833100")        # Detects CUSIP
result = registry.resolve("AAPL", "XNAS")     # Detects ticker
result = registry.resolve("BBG000B9XRY4")     # Detects FIGI

# Get identifier coverage statistics
coverage = registry.identifier_coverage()
print(coverage["isin"]["percentage"])    # 100.0
print(coverage["cusip"]["percentage"])   # 86.0

# Find tickers with multiple exchange listings
ambiguous = registry.tickers_with_multiple_listings()
print(ambiguous)  # ['PRU']
```

## API Reference

### Constructor

```python
AssetRegistry(path: str | Path = "identifiers.json")
```

Loads the registry from a JSON file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` or `Path` | Path to `identifiers.json` |

**Raises:**
- `FileNotFoundError` — if the path does not exist
- `json.JSONDecodeError` — if the file is not valid JSON

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `count` | `int` | Number of instruments |
| `instruments` | `List[Dict]` | All instrument dicts |
| `path` | `Path` | Registry file path |

### Lookup Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `by_isin(isin)` | `Dict \| None` | Look up by ISIN |
| `by_cusip(cusip)` | `Dict \| None` | Look up by CUSIP |
| `by_sedol(sedol)` | `Dict \| None` | Look up by SEDOL |
| `by_figi(figi)` | `Dict \| None` | Look up by FIGI |
| `by_lei(lei)` | `Dict \| None` | Look up by LEI |
| `by_ticker(ticker, exchange=None)` | `Dict \| List[Dict] \| None` | Look up by ticker |

### Filter Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `by_exchange(exchange)` | `List[Dict]` | All instruments on an exchange |
| `by_asset_class(asset_class)` | `List[Dict]` | All instruments of an asset class |
| `by_country(country)` | `List[Dict]` | All instruments from a country |
| `by_currency(currency)` | `List[Dict]` | All instruments in a currency |

### Bulk Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `all()` | `List[Dict]` | All instruments |

### Metadata Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `meta()` | `Dict` | Full metadata |
| `version()` | `str` | Registry version |
| `generated()` | `str` | Generation date |
| `sources()` | `List[str]` | Data sources |

### Aggregate Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `exchanges()` | `List[str]` | Sorted list of MIC codes |
| `asset_classes()` | `List[str]` | Sorted list of asset classes |
| `currencies()` | `List[str]` | Sorted list of currency codes |
| `countries()` | `List[str]` | Sorted list of country codes |

### Convenience Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `resolve(identifier, exchange=None)` | `Dict \| List[Dict] \| None` | Auto-detect identifier type |
| `ticker_exists(ticker, exchange=None)` | `bool` | Check ticker exists |
| `isin_exists(isin)` | `bool` | Check ISIN exists |
| `identifier_coverage()` | `Dict` | Coverage statistics |
| `tickers_with_multiple_listings()` | `List[str]` | Ambiguous tickers |

### Dunder Methods

| Method | Description |
|--------|-------------|
| `__len__()` | Returns `count` |
| `__iter__()` | Iterates over all instruments |
| `__repr__()` | String representation |
| `__str__()` | Human-readable representation |

## Handling Duplicate Tickers

Some tickers are ambiguous — the same symbol exists on multiple exchanges. The registry handles this correctly.

```python
# PRU exists on both London and New York
result = registry.by_ticker("PRU")
# Returns: [
#   {"ticker": "PRU", "exchange": "XLON", "isin": "GB0007099541", ...},
#   {"ticker": "PRU", "exchange": "XNYS", "isin": "US7443201022", ...}
# ]

# Disambiguate by exchange
london = registry.by_ticker("PRU", "XLON")   # Returns single dict
new_york = registry.by_ticker("PRU", "XNYS")  # Returns single dict

# Check if a ticker is ambiguous
ambiguous = registry.tickers_with_multiple_listings()
print(ambiguous)  # ['PRU']
```

## Handling Ticker Changes

The registry preserves historical ticker changes. The ISIN remains permanent even when the ticker changes.

```python
# Meta Platforms changed from FB to META in 2022
meta = registry.by_isin("US30303M1027")
print(meta["ticker"])  # META

# But history contains the old ticker
history = meta.get("history", [])
for event in history:
    print(event["ticker"], event["change_date"], event["change_type"])
# Output:
# FB    2012-05-18  none
# META  2022-06-09  rename

# The ISIN never changed
print(meta["isin"])  # US30303M1027
```

## Multi-Exchange Listings

Some instruments are listed on multiple exchanges.

```python
# Apple is listed on NASDAQ (primary) and XETRA (secondary)
aapl = registry.by_isin("US0378331005")
listings = aapl.get("listings", [])

for listing in listings:
    print(listing["exchange"], listing["ticker"], listing["currency"], listing["status"])
# Output:
# XNAS  AAPL  USD  PRIMARY
# XETR  APC   EUR  SECONDARY
```

## Identifier Coverage

Check how complete the registry is:

```python
coverage = registry.identifier_coverage()

for identifier_type, stats in coverage.items():
    print(f"{identifier_type.upper()}: {stats['covered']}/{stats['total']} ({stats['percentage']}%)")

# Output:
# ISIN:  50/50 (100.0%)
# CUSIP: 43/50 (86.0%)
# SEDOL: 0/50 (0.0%)
# FIGI:  49/50 (98.0%)
# LEI:   50/50 (100.0%)
```

## Dependencies

None. This wrapper uses only the Python standard library (`json`, `pathlib`, `typing`).

## Python Version Support

- Python 3.8+
- Python 3.9+
- Python 3.10+
- Python 3.11+
- Python 3.12+
- Python 3.13+

## Type Hints

The wrapper includes full type hints. Use `mypy` for static type checking:

```bash
pip install mypy
mypy asset_identifiers/registry.py
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run only wrapper tests
pytest tests/test_wrappers.py -v

# Run with coverage
pytest tests/ --cov=asset_identifiers --cov-report=term-missing
```

## License

Apache 2.0 — see [LICENSE](../../LICENSE) for full text.

## Author

**Le P'tit** — [github.com/slimissa](https://github.com/slimissa)

## Links

- [Main Repository](https://github.com/slimissa/asset-identifiers)
- [Issue Tracker](https://github.com/slimissa/asset-identifiers/issues)
- [CHANGELOG](../../CHANGELOG.md)
- [Contributing Guide](../../CONTRIBUTING.md)
