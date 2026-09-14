# Asset Identifier Registry

**A versioned, schema-validated toolkit for mapping financial instruments to their standard identifiers — ISIN, CUSIP, SEDOL, FIGI, LEI, and ticker symbols.**

Schema. Validator. Four language wrappers. Synthetic test fixture. Bring your own data.

[![Validate](https://github.com/slimissa/asset-identifiers/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/asset-identifiers/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Schema Version](https://img.shields.io/badge/schema-1.2.1-green.svg)](./schema.json)
[![Data](https://img.shields.io/badge/data-bring_your_own-lightgrey.svg)](./DATA_LICENSE.md)

---

## Data — Read First

**This repository does not ship identifier data.**

The code, schema, validator, test fixture, and four wrappers are Apache 2.0. The instrument data is not — it is subject to vendor licenses (CUSIP Global Services, Bloomberg FIGI, GLEIF, FMP) that prohibit public redistribution.

See [DATA_LICENSE.md](./DATA_LICENSE.md) and [docs/decisions/0001-data-license.md](./docs/decisions/0001-data-license.md) for the full policy.

### What this means for you

| You want to… | What you do |
|---|---|
| Develop against the toolkit | Use the synthetic fixture. No data file needed. Tests run out of the box. |
| Use real identifiers | Supply your own `identifiers.json` under a license that permits your use. |
| Integrate with LAS_Shell / Tempus | Set `$LAS_IDENTIFIERS` (or `$TEMPUS_DATA_HOME`) to your data file. |

The schema is the contract. Any file conforming to [`schema.json`](./schema.json) works with every wrapper.

---

## Why?

Every trading system, quant library, and fintech app maintains its own mapping of tickers to permanent identifiers. They are often outdated, inconsistent, or silently wrong.

| Problem | Example |
|---------|---------|
| Ticker changes | `FB` → `META` (June 2022) — the ISIN stayed the same |
| Duplicate tickers | `PRU` = Prudential plc (London) *and* Prudential Financial (NYSE) |
| Exchange-specific tickers | `AAPL` on NASDAQ, `APC` on XETRA — same ISIN |
| Missing identifiers | Ticker exists, ISIN/CUSIP/FIGI missing |
| Invalid check digits | ISIN that passes format validation but fails Luhn |

**This project provides a schema, a validator, and four language wrappers that any tool can depend on — instead of every project hand-rolling its own.**

- **LAS_Shell** — audit logs with permanent identifiers, risk configs that survive ticker changes
- **Tempus** — compile-time `Security<ISIN>` type validation
- **Python quant libraries** — identifier resolution and check-digit validation
- **Go trading systems** — order routing by permanent ID
- **Rust finance crates** — type-safe instrument lookups
- **JavaScript fintech apps** — portfolio display with canonical symbols

The registry is language-agnostic. The JSON is the contract. The wrappers are the interface.

---

## Quick Start

### Try it with the fixture (no setup)

The repository ships a synthetic fixture with seven fake instruments. Every wrapper loads it out of the box.

```python
from asset_identifiers import AssetRegistry

registry = AssetRegistry("tests/fixtures/identifiers.test.json")

testa = registry.by_isin("US0000000002")
print(testa["ticker"])   # TESTA
print(testa["name"])     # Synthetic Test A
```

```bash
pytest tests/ -q
# 144 passed, 1 skipped
```

### Use it with real data

Set `$LAS_DATA_HOME` to a directory containing your licensed `identifiers.json`:

```bash
export LAS_DATA_HOME="$HOME/Documents/asset-identifiers-data"
export LAS_IDENTIFIERS="$LAS_DATA_HOME/identifiers.json"
```

Then any wrapper reads from there:

```python
import os
from asset_identifiers import AssetRegistry

registry = AssetRegistry(os.environ["LAS_IDENTIFIERS"])

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

const registry = new AssetRegistry(process.env.LAS_IDENTIFIERS);

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
use std::env;

let path = env::var("LAS_IDENTIFIERS")?;
let registry = AssetRegistry::load(&path)?;
let aapl = registry.by_isin("US0378331005").unwrap();
println!("{}", aapl.ticker);  // AAPL
```

```bash
cargo add asset-identifiers
```

### Go

```go
import (
    "os"
    assetidentifiers "github.com/slimissa/asset-identifiers-go"
)

path := os.Getenv("LAS_IDENTIFIERS")
registry, _ := assetidentifiers.LoadRegistry(path)
aapl, _ := registry.ByIsin("US0378331005")
fmt.Println(aapl.Ticker)  // AAPL
```

```bash
go get github.com/slimissa/asset-identifiers-go
```

---

## Repository Contents

This repository contains **code, schema, tests, and documentation** — no data.

| Component | Language | Purpose |
|-----------|----------|---------|
| `schema.json` | JSON Schema | Data format contract |
| `tools/validate.py` | Python | 7-layer validation (schema, check digits, uniqueness, business rules, coverage, temporal, cross-registry) |
| `tools/build.py` | Python | Merge history, rebuild artifacts |
| `tools/gen_test_fixture.py` | Python | Generate the synthetic test fixture |
| `wrappers/python/` | Python | `pip install asset-identifiers-registry` |
| `wrappers/javascript/` | JavaScript | `npm install asset-identifiers-registry` |
| `wrappers/rust/` | Rust | `cargo add asset-identifiers` |
| `wrappers/go/` | Go | `go get github.com/slimissa/asset-identifiers-go` |
| `tests/fixtures/identifiers.test.json` | Fixture | Seven synthetic instruments for testing |
| `tests/` | Python | Root test suite |
| `docs/decisions/` | Markdown | Architecture decision records |

### What the schema supports

An instrument entry carries:

- **Identifiers** — `isin`, `cusip`, `sedol`, `figi`, `lei`, `cik` (nullable during enrichment)
- **Identity** — `ticker`, `exchange` (ISO 10383 MIC), `name`, `currency` (ISO 4217), `country`
- **Classification** — `asset_class` (`equity` / `etf` / `bond` / `option` / `future` / `other`), `instrument_type`, `sector`, `industry`
- **Status** — `active`, `listing_date`, `delisting_date`
- **Structure** — `listings[]` for primary and secondary listings across exchanges
- **History** — `history[]` for ticker changes with dates, reasons, sources
- **Corporate actions** — `corporate_actions[]` for splits, mergers, spinoffs

Example entry:

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
      "status": "PRIMARY",
      "listing_date": "1980-12-12",
      "delisting_date": null
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
  "corporate_actions": []
}
```

The full schema is in [`schema.json`](./schema.json).

---

## Features

### 1. Ticker change history

The ISIN is permanent. The ticker is not.

```python
meta = registry.by_isin("US30303M1027")
print(meta["ticker"])  # META

for event in meta["history"]:
    print(event["ticker"], event["change_date"], event["change_type"])
# FB    2012-05-18  none
# META  2022-06-09  rename
```

### 2. Duplicate ticker disambiguation

The same ticker can exist on multiple exchanges, for different legal entities.

```python
pru_all = registry.by_ticker("PRU")
print(len(pru_all))  # 2

pru_london = registry.by_ticker("PRU", "XLON")
print(pru_london["isin"])  # GB0007099541

pru_nyse = registry.by_ticker("PRU", "XNYS")
print(pru_nyse["isin"])    # US7443201022
```

### 3. Multi-exchange listings

A single ISIN can trade on multiple venues, in different currencies.

```python
aapl = registry.by_isin("US0378331005")
for listing in aapl["listings"]:
    print(listing["exchange"], listing["ticker"], listing["currency"])
# XNAS  AAPL  USD
# XETR  APC   EUR
```

### 4. Check-digit validation

All identifiers are validated against their official algorithms.

| Identifier | Algorithm | Standard |
|-----------|-----------|----------|
| ISIN | Luhn (modified, letters → digits) | ISO 6166 |
| CUSIP | Luhn (modified, multi-digit letter expansion) | ANSI X9.6 |
| SEDOL | Weighted sum, no vowels | London Stock Exchange |
| FIGI | Bloomberg proprietary | OpenFIGI |
| LEI | ISO 17442 | GLEIF |

```python
from tools.validate import (
    validate_isin_check_digit,
    validate_cusip_check_digit,
    validate_sedol_check_digit,
)

validate_isin_check_digit("US0378331005")   # True
validate_cusip_check_digit("037833100")     # True
validate_sedol_check_digit("2046251")       # True
```

### 5. Cross-registry validation

When the sibling registries are present, the validator checks:

- Currencies against [ISO 4217](https://github.com/slimissa/iso4217)
- Exchange MICs against [Exchange Calendar](https://github.com/slimissa/exchange-calendar)

```bash
python3 tools/validate.py --verbose
# OK: N instrument(s) validated successfully
#      ISO 4217 currencies loaded: 167
#      Exchange MICs loaded: 74
```

### 6. Nullable identifiers during enrichment

A record can exist as a skeleton with `isin: null` before it is enriched. The schema allows this. The country-identifier rule only fires on records that have an ISIN.

This lets a registry be built progressively from multiple fetchers (SEC EDGAR adds skeletons; FMP fills ISIN and CUSIP; OpenFIGI fills FIGI; GLEIF fills LEI) without invalid intermediate states.

---

## Validation

Multi-layer defense:

| Layer | What it checks | Tool |
|-------|----------------|------|
| **JSON Schema** | Structure, types, required fields, formats | `schema.json` + `jsonschema` |
| **Check digits** | Mathematical validity of ISIN / CUSIP / SEDOL | `tools/validate.py` |
| **Uniqueness** | No duplicate ISIN / CUSIP / SEDOL / FIGI / ticker+exchange | `tools/validate.py` |
| **Business rules** | Country-specific identifier requirements (using ISIN prefix, not the country field) | `tools/validate.py` |
| **Coverage** | `meta.coverage` matches the actual data | `tools/validate.py` |
| **Temporal** | History ordering, listing before delisting, first event `none` | `tools/validate.py` |
| **Cross-registry** | Currencies against ISO 4217, MICs against Exchange Calendar | `tools/validate.py` |

```bash
# Validate a data file
python3 tools/validate.py --data "$LAS_IDENTIFIERS" --verbose

# Rebuild distribution artifacts
python3 tools/build.py --data "$LAS_IDENTIFIERS"
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Validation passed |
| 1 | Data errors (check digits, uniqueness, business rules) |
| 2 | Usage error (missing file, bad arguments) |
| 3 | Schema violation |

---

## Tests

The test suite runs entirely against the synthetic fixture at `tests/fixtures/identifiers.test.json`. No data file is required.

| Suite | Tests | Result |
|-------|-------|--------|
| Python — root suite | 144 | ✅ pass, 1 skipped |
| JavaScript — wrapper | 67 | ✅ pass |
| Rust — wrapper (lib) | 16 | ✅ pass |
| Rust — doctests | 3 | ✅ pass |
| Go — wrapper | passing | ✅ pass |

```bash
# Python
pytest tests/ -q

# JavaScript
(cd wrappers/javascript && npm test)

# Rust
(cd wrappers/rust && cargo test)

# Go
(cd wrappers/go && go clean -testcache && go test ./...)
```

### Fixture-anchor rule

Tests must not hardcode fixture values. Every assertion reads its expected value from a per-language anchor module derived from the fixture at load time.

| Language | Anchor module |
|----------|---------------|
| Python | `tests/fixture.py` |
| JavaScript | `wrappers/javascript/test/fixture.js` |
| Rust | `mod fixture` inside `wrappers/rust/src/lib.rs` |
| Go | `mustByTickerExchange` in `wrappers/go/registry_test.go` |

If the fixture changes, the anchors change with it, and the tests stay correct without editing. A missing anchor fails loudly at startup, not silently.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details and the drift-test procedure.

---

## Project Structure

```
asset-identifiers/
├── schema.json                       # Data format contract
├── DATA_LICENSE.md                   # Data licensing policy
├── CONTRIBUTING.md                   # Anchor rule, drift test, PR process
├── README.md                         # This file
├── LICENSE                           # Apache 2.0 (code only)
├── CHANGELOG.md
│
├── tools/
│   ├── validate.py                   # 7-layer validator
│   ├── build.py                      # Merge history, rebuild artifacts
│   ├── gen_test_fixture.py           # Generate the synthetic fixture
│   ├── fetch_sec_edgar.py            # SEC EDGAR fetcher (public data)
│   ├── fetch_fmp_profile.py          # FMP fetcher (licensed data, writes to $LAS_DATA_HOME)
│   ├── fetch_openfigi_batch.py       # OpenFIGI fetcher (FIGI enrichment)
│   └── fetch_gleif_lei.py            # GLEIF fetcher (LEI enrichment)
│
├── wrappers/
│   ├── python/                       # pip install asset-identifiers-registry
│   ├── javascript/                   # npm install asset-identifiers-registry
│   ├── rust/                         # cargo add asset-identifiers
│   └── go/                           # go get github.com/slimissa/asset-identifiers-go
│
├── tests/
│   ├── fixture.py                    # Fixture-derived test anchors
│   ├── fixtures/
│   │   └── identifiers.test.json     # Synthetic fixture (7 instruments)
│   ├── test_check_digits.py          # Algorithm tests
│   ├── test_registry.py              # Registry structure and metadata
│   ├── test_cross_reference.py       # ISIN ↔ CUSIP ↔ FIGI relationships
│   └── test_wrappers.py              # Wrapper API and consistency
│
├── docs/
│   └── decisions/
│       └── 0001-data-license.md      # ADR: private data, public code
│
└── .github/
    └── workflows/
        └── validate.yml              # CI on every push
```

---

## Versioning

Two independent version numbers:

| Version | Meaning | Where |
|---------|---------|-------|
| **Schema** | Format contract. Bumped when a field is added or changed. | `schema.json` → `$id` or metadata |
| **Data** | The user's `identifiers.json`. Bumped by their own process. | `identifiers.json` → `meta.version` |

The schema follows [Semantic Versioning](https://semver.org/):

- **Major** — breaking format change
- **Minor** — new optional field
- **Patch** — validation rule clarification

The toolkit does not version independently of the schema; wrapper releases track schema compatibility.

---

## Integrations

| Project | How it uses this toolkit |
|---------|--------------------------|
| **LAS_Shell** | Reads `$LAS_IDENTIFIERS` for audit logs, risk config, and the `identifier` built-in |
| **Tempus** | Reads `$TEMPUS_DATA_HOME/identifiers.json` for compile-time `Security<ISIN>` validation |
| **Corporate Actions Registry** | Cross-validates ISINs against this schema |

*Using this toolkit in your project? Open a PR to add your name here.*

---

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| **v1.0.0** | Schema, validator, four wrappers, synthetic fixture, anchor-based tests, ADR | ✅ Shipped |
| **v1.1.0** | International schema extensions (multi-currency listings, dual-share classes) | Planned |
| **v1.2.0** | Package publication to PyPI, npm, crates.io, Go modules | Planned |
| **v2.0.0** | Streaming updates, real-time synchronization, LAS_Shell audit integration | Planned |

SEDOL enrichment is **not on the roadmap** — it requires an LSE Masterfile license that is not currently available.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for:

- The fixture-anchor rule and why it exists
- The drift test procedure
- Data quality rules for fixture additions
- The wrapper API contract
- Pull request process

**Do not commit licensed identifier data.** PRs that add real ISINs, CUSIPs, FIGIs, or LEIs sourced from a vendor will be rejected. See [DATA_LICENSE.md](./DATA_LICENSE.md).

---

## License

**Code** (schema, tools, wrappers, tests, documentation): Apache 2.0. Use it anywhere, no attribution required.

**Data**: not distributed by this repository. Users supply their own under their own license.

The two are deliberately separate. See [DATA_LICENSE.md](./DATA_LICENSE.md) and [docs/decisions/0001-data-license.md](./docs/decisions/0001-data-license.md).

---

## Author

**Le P'tit** — [github.com/slimissa](https://github.com/slimissa)

## Links

- [GitHub Repository](https://github.com/slimissa/asset-identifiers)
- [Issue Tracker](https://github.com/slimissa/asset-identifiers/issues)
- [CI Status](https://github.com/slimissa/asset-identifiers/actions)
- [CHANGELOG.md](./CHANGELOG.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [DATA_LICENSE.md](./DATA_LICENSE.md)
- [ADR 0001 — Data licensing model](./docs/decisions/0001-data-license.md)