# Asset Identifier Registry

**A canonical, versioned, machine-readable registry mapping financial instruments to their standard identifiers — ISIN, CUSIP, SEDOL, FIGI, LEI, and ticker symbols.**

One JSON file. Zero runtime dependencies. Four language wrappers.
Fifty instruments. 292 tests.

[![Validate](https://github.com/slimissa/asset-identifiers/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/asset-identifiers/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Schema Version](https://img.shields.io/badge/schema-1.0.0-green.svg)](./schema.json)
[![Registry Version](https://img.shields.io/badge/registry-1.0.0-orange.svg)](./identifiers.json)
[![Tests](https://img.shields.io/badge/tests-292-green.svg)](./tests/)

---

## Why?

Every trading system, quant library, and fintech app maintains its own mapping of tickers to permanent identifiers. They are often outdated, inconsistent, or just wrong.

| Problem | Example |
|---------|---------|
| Ticker changes | `FB` → `META` (June 2022) |
| Duplicate tickers | `PRU` = Prudential plc (London) AND Prudential Financial (NYSE) |
| Exchange-specific tickers | `AAPL` on NASDAQ, `APC` on XETRA |
| Missing identifiers | Ticker exists, but ISIN/CUSIP/FIGI missing |
| Invalid check digits | Wrong ISIN that passes format but fails Luhn validation |

**This project provides one versioned, schema-validated registry that any tool can depend on — instead of every project hand-rolling and hand-maintaining its own.**

- **Las_shell** uses it for audit logs with permanent identifiers
- **Tempus** uses it for compile-time `Security<ISIN>` validation
- **Python quant libraries** use it for identifier resolution
- **Go trading systems** use it for order routing
- **Rust finance crates** use it for type-safe instrument lookups
- **JavaScript fintech apps** use it for portfolio display

The registry is language-agnostic by design. The JSON is the contract.

---

## Quick Start

### Direct download

```bash
curl -O https://raw.githubusercontent.com/slimissa/asset-identifiers/main/identifiers.json
```

### Python

```python
from asset_identifiers import AssetRegistry

registry = AssetRegistry("identifiers.json")

aapl = registry.by_isin("US0378331005")
print(aapl["ticker"])   # AAPL
print(aapl["name"])     # Apple Inc.

pru = registry.by_ticker("PRU", "XNYS")
print(pru["isin"])      # US7443201022
```

```bash
pip install asset-identifiers-registry
```

### JavaScript

```javascript
const { AssetRegistry } = require('asset-identifiers-registry');

const registry = new AssetRegistry('identifiers.json');

const aapl = registry.byIsin('US0378331005');
console.log(aapl.ticker);  // AAPL

const pru = registry.byTicker('PRU', 'XLON');
console.log(pru.isin);     // GB0007099541
```

```bash
npm install asset-identifiers-registry
```

### Rust

```rust
use asset_identifiers::AssetRegistry;

let registry = AssetRegistry::load("identifiers.json")?;
let aapl = registry.by_isin("US0378331005").unwrap();
println!("{}", aapl.ticker);  // AAPL
```

```bash
cargo add asset-identifiers
```

### Go

```go
import assetidentifiers "github.com/slimissa/asset-identifiers-go"

registry, _ := assetidentifiers.LoadRegistry("identifiers.json")
aapl, _ := registry.ByIsin("US0378331005")
fmt.Println(aapl.Ticker)  // AAPL
```

```bash
go get github.com/slimissa/asset-identifiers-go
```

---

## Registry Contents

| Category | Count | Description |
|----------|-------|-------------|
| US Equities | 40 | Major US-listed stocks (S&P 500, NASDAQ 100) |
| ETFs | 10 | SPY, QQQ, IWM, VTI, VEA |
| International Equities | 10 | UK, Japan, Germany, France, Switzerland, Hong Kong, Korea |
| **Total** | **50** | |

### Coverage

| Exchange | Region | Instruments |
|----------|--------|-------------|
| XNAS (NASDAQ) | North America | 19 |
| XNYS (NYSE) | North America | 24 |
| XLON (London) | Europe | 1 |
| XETR (Deutsche Börse) | Europe | 1 |
| XPAR (Euronext Paris) | Europe | 1 |
| XSWX (SIX Swiss) | Europe | 1 |
| XTKS (Tokyo) | Asia | 1 |
| XHKG (Hong Kong) | Asia | 1 |
| XKRX (Korea) | Asia | 1 |

### Identifier Coverage

| Identifier | Coverage | Description |
|-----------|----------|-------------|
| ISIN | 100% | All instruments have ISIN |
| CUSIP | 86% | US/Canada instruments only |
| SEDOL | 0% | Not yet populated (requires LSE Masterfile) |
| FIGI | 98% | 49/50 instruments |
| LEI | 100% | All instruments have LEI |

---

## What's in an instrument entry

```json
{
  "isin": "US0378331005",
  "cusip": "037833100",
  "sedol": null,
  "figi": "BBG000B9XRY4",
  "lei": "HWUPKR0MPOU8FGXBT394",
  "ticker": "AAPL",
  "exchange": "XNAS",
  "name": "Apple Inc.",
  "currency": "USD",
  "asset_class": "equity",
  "instrument_type": "COMMON_STOCK",
  "sector": "TECHNOLOGY",
  "industry": "CONSUMER_ELECTRONICS",
  "country": "US",
  "active": true,
  "listing_date": "1980-12-12",
  "delisting_date": null,
  "listings": [
    {
      "exchange": "XNAS",
      "ticker": "AAPL",
      "currency": "USD",
      "status": "PRIMARY"
    },
    {
      "exchange": "XETR",
      "ticker": "APC",
      "currency": "EUR",
      "status": "SECONDARY"
    }
  ],
  "history": [
    {
      "ticker": "AAPL",
      "change_date": "1980-12-12",
      "change_type": "none",
      "reason": "INITIAL_LISTING",
      "source": "NASDAQ",
      "source_url": "https://www.nasdaq.com/market-activity/stocks/aapl"
    }
  ],
  "corporate_actions": [
    {
      "date": "2020-08-31",
      "action_type": "SPLIT",
      "ratio": "4:1",
      "details": "Four-for-one stock split",
      "source": "Apple Inc. press release",
      "source_url": "https://www.apple.com/newsroom/2020/07/apple-announces-four-for-one-stock-split/"
    }
  ]
}
```

---

## Features

### 1. Ticker Change History

The registry preserves historical ticker changes. The ISIN remains permanent.

```python
meta = registry.by_isin("US30303M1027")
print(meta["ticker"])  # META

for event in meta["history"]:
    print(event["ticker"], event["change_date"], event["change_type"])
# FB    2012-05-18  none
# META  2022-06-09  rename
```

### 2. Duplicate Ticker Disambiguation

The same ticker can exist on multiple exchanges with different instruments.

```python
pru_all = registry.by_ticker("PRU")
print(len(pru_all))  # 2

pru_london = registry.by_ticker("PRU", "XLON")
print(pru_london["isin"])  # GB0007099541

pru_nyse = registry.by_ticker("PRU", "XNYS")
print(pru_nyse["isin"])  # US7443201022
```

### 3. Multi-Exchange Listings

Instruments can have primary and secondary listings.

```python
aapl = registry.by_isin("US0378331005")
for listing in aapl["listings"]:
    print(listing["exchange"], listing["ticker"], listing["currency"])
# XNAS  AAPL  USD
# XETR  APC   EUR
```

### 4. Corporate Actions

Splits, mergers, and spinoffs are recorded with dates and ratios.

```python
nvda = registry.by_isin("US67066G1040")
for action in nvda["corporate_actions"]:
    print(action["date"], action["action_type"], action["ratio"])
# 2021-07-20  SPLIT  4:1
# 2024-06-10  SPLIT  10:1
```

### 5. Check-Digit Validation

All identifiers are validated against their official algorithms:

| Identifier | Algorithm | Standard |
|-----------|-----------|----------|
| ISIN | Luhn (modified) | ISO 6166 |
| CUSIP | Luhn (modified) | ANSI X9.6 |
| SEDOL | Weighted sum | London Stock Exchange |
| FIGI | Bloomberg proprietary | OpenFIGI |
| LEI | ISO 17442 | GLEIF |

---

## Validation

The registry is validated through a multi-layer defense:

| Layer | What It Checks | Tool |
|-------|---------------|------|
| **JSON Schema** | Structure, types, required fields | `schema.json` |
| **Check digits** | Mathematical validity of ISIN/CUSIP/SEDOL | `tools/validate.py` |
| **Uniqueness** | No duplicate identifiers | `tools/validate.py` |
| **Business rules** | Country-specific identifier requirements | `tools/validate.py` |
| **Coverage** | Meta coverage matches actual data | `tools/validate.py` |
| **Temporal** | History ordering, listing/delisting dates | `tools/validate.py` |
| **Cross-language** | All wrappers return identical results | `tests/cross_language_consistency.json` |

```bash
# Run all validations
python3 tools/validate.py --verbose

# Run the full test suite (292 tests)
pytest tests/ -v
cd wrappers/javascript && npm test
cd wrappers/rust && cargo test
cd wrappers/go && go test ./...
```

---

## Project Structure

```
asset-identifiers/
├── identifiers.json              # The registry — single source of truth
├── schema.json                   # JSON Schema for validation
│
├── history/
│   └── ticker_changes.json       # Ticker change event log
│
├── tools/
│   ├── validate.py               # Schema + check-digit + business rule validation
│   ├── build.py                  # Build distribution artifacts
│   └── fetch_identifiers.py      # Fetch data from OpenFIGI
│
├── wrappers/
│   ├── python/                   # pip install asset-identifiers-registry
│   ├── javascript/               # npm install asset-identifiers-registry
│   ├── rust/                     # cargo add asset-identifiers
│   └── go/                       # go get github.com/slimissa/asset-identifiers-go
│
├── tests/
│   ├── test_check_digits.py      # ISIN/CUSIP/SEDOL algorithm tests (23)
│   ├── test_registry.py          # Data validation tests (73)
│   ├── test_cross_reference.py   # Identifier relationship tests (39)
│   ├── test_wrappers.py          # Wrapper API tests (24)
│   └── cross_language_consistency.json
│
├── examples/
│   ├── python_lookup.py
│   ├── javascript_lookup.js
│   ├── rust_lookup.rs
│   └── go_lookup.go
│
├── docs/
│   └── validation_algorithms.md  # Check-digit algorithm specifications
│
├── .github/
│   ├── workflows/
│   │   └── validate.yml          # CI: 292 tests on every push
│   └── ISSUE_TEMPLATE/
│       └── identifier_update.md  # Structured update requests
│
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                       # Apache 2.0
└── README.md
```

---

## Tests

| Suite | Tests | Status |
|-------|-------|--------|
| Python — check digits | 23 | ✅ All pass |
| Python — registry data | 73 | ✅ All pass |
| Python — cross-reference | 39 | ✅ All pass |
| Python — wrapper API | 24 | ✅ All pass |
| JavaScript — wrapper | 72 | ✅ All pass |
| Rust — wrapper | 19 | ✅ All pass |
| Go — wrapper | 42 | ✅ All pass |
| **Total** | **292** | ✅ **Zero failures** |

```bash
# Python (159 tests)
pytest tests/ -v

# JavaScript (72 tests)
cd wrappers/javascript && npm test

# Rust (19 tests)
cd wrappers/rust && cargo test

# Go (42 tests)
cd wrappers/go && go test ./... -v
```

---

## Versioning

The registry follows [Semantic Versioning](https://semver.org/):
- **Major**: Instruments added or removed
- **Minor**: New optional fields added
- **Patch**: Data corrections

Current version: **1.0.0** (see `identifiers.json` → `meta.version`)

---

## Adopted By

| Project | How It Uses This Registry |
|---------|--------------------------|
| **Las_shell** *(planned)* | Audit logs with permanent identifiers, risk configs that survive ticker changes |
| **Tempus** *(planned)* | Compile-time `Security<ISIN>` type validation |

*Using this registry in your project? Open a PR to add your name here.*

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on:
- Data corrections
- New instruments
- Wrapper improvements
- Tooling enhancements

**Quick correction workflow:**
1. Edit `identifiers.json`
2. Run `python3 tools/validate.py` — must pass with 0 errors
3. Run `pytest tests/ -v` — all tests must pass
4. Submit a PR with your source cited

---

## License

Apache 2.0 — use it anywhere, no attribution required. The instrument data in this registry is factual information sourced from official exchange and regulatory filings. The compilation, schema, tooling, and wrappers are licensed works.

## Author

**Le P'tit** — [github.com/slimissa](https://github.com/slimissa)

## Links

- [GitHub Repository](https://github.com/slimissa/asset-identifiers)
- [Issue Tracker](https://github.com/slimissa/asset-identifiers/issues)
- [CI Status](https://github.com/slimissa/asset-identifiers/actions)
- [CHANGELOG.md](CHANGELOG.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
