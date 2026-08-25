# Contributing to Asset Identifier Registry

Thank you for your interest in contributing to the Asset Identifier Registry. This document provides guidelines for submitting corrections, additions, and improvements.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Ways to Contribute](#ways-to-contribute)
3. [Quick Correction Workflow](#quick-correction-workflow)
4. [Adding a New Instrument](#adding-a-new-instrument)
5. [Correcting an Identifier](#correcting-an-identifier)
6. [Data Quality Rules](#data-quality-rules)
7. [Wrapper Contributions](#wrapper-contributions)
8. [Testing Requirements](#testing-requirements)
9. [Pull Request Process](#pull-request-process)
10. [Style Guidelines](#style-guidelines)

---

## Code of Conduct

This project adheres to a simple code of conduct:

- Be respectful
- Be constructive
- Cite your sources
- Verify your data

---

## Ways to Contribute

| Contribution Type | Description | Effort |
|------------------|-------------|--------|
| **Data correction** | Fix a wrong ISIN, CUSIP, ticker, or metadata | Low |
| **New instrument** | Add a new instrument to the registry | Low |
| **New wrapper** | Port the wrapper to another language | High |
| **Tooling improvement** | Improve validation, build, or fetch tools | Medium |
| **Test improvement** | Add more test coverage | Medium |
| **Documentation** | Fix or improve docs | Low |

---

## Quick Correction Workflow

The fastest way to submit a data correction:

### Step 1: Open an issue

Use the [Identifier Update template](https://github.com/slimissa/asset-identifiers/issues/new?template=identifier_update.md).

### Step 2: Provide the source

Every data change **requires** an official source URL:

- Exchange announcement (NASDAQ, NYSE, LSE, etc.)
- SEC filing (EDGAR)
- Company press release (Investor Relations page)
- Regulatory filing (GLEIF for LEI, ANNA for ISIN)

### Step 3: Wait for review

A maintainer will verify the source and apply the change.

### Step 4: CI validation

The CI pipeline runs automatically:
- `python3 tools/validate.py` — registry validation
- `pytest tests/ -v` — 159 Python tests
- `npm test` — 72 JavaScript tests
- `cargo test` — 19 Rust tests
- `go test ./...` — 42 Go tests

---

## Adding a New Instrument

### Required Fields

Every new instrument **must** include:

| Field | Required | Description |
|-------|----------|-------------|
| `isin` | ✅ | 12-character ISIN with valid check digit |
| `ticker` | ✅ | Current ticker on primary exchange |
| `exchange` | ✅ | MIC code (4 characters) |
| `name` | ✅ | Legal entity name |
| `currency` | ✅ | ISO 4217 currency code |
| `asset_class` | ✅ | equity, etf, bond, option, future, other |
| `active` | ✅ | Boolean |
| `cusip` | Conditional | Required for US/Canada instruments |
| `sedol` | Conditional | Required for UK/Europe instruments |
| `figi` | Recommended | 12-character FIGI |
| `lei` | Recommended | 20-character LEI |
| `country` | Recommended | ISO 3166-1 alpha-2 |
| `listings` | Recommended | Full listing history |
| `history` | ✅ | At least one entry with `change_type: "none"` |
| `source_url` | ✅ | Official source for the data |

### Example

```json
{
  "isin": "US0378331005",
  "cusip": "037833100",
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

---

## Correcting an Identifier

### Check-digit validation

Before submitting a correction, verify the check digit:

```bash
# Validate an ISIN
python3 -c "
import sys
sys.path.insert(0, 'tools')
from validate import validate_isin_check_digit
print(validate_isin_check_digit('US0378331005'))
"

# Validate a CUSIP
python3 -c "
import sys
sys.path.insert(0, 'tools')
from validate import validate_cusip_check_digit
print(validate_cusip_check_digit('037833100'))
"

# Validate a SEDOL
python3 -c "
import sys
sys.path.insert(0, 'tools')
from validate import validate_sedol_check_digit
print(validate_sedol_check_digit('2046251'))
"
```

### What cannot be corrected without a source

- ISIN changes without an official announcement
- Ticker changes without an exchange filing
- Delistings without an exchange notice
- Corporate actions without a press release

---

## Data Quality Rules

### Rule 1: Source URL Required

Every explicit data entry **must** have a `source_url` pointing to an official source.

### Rule 2: Check Digits Must Validate

All ISIN, CUSIP, and SEDOL values must pass their respective check-digit algorithms.

### Rule 3: No Duplicates

No two instruments may share the same ISIN, CUSIP, SEDOL, FIGI, or LEI.

### Rule 4: Ticker+Exchange Pairs Must Be Unique

The same ticker may appear on different exchanges (e.g., PRU on XLON and XNYS), but the pair (ticker, exchange) must be unique.

### Rule 5: US Instruments Require CUSIP

Instruments with country "US" or "CA" must have a CUSIP.

### Rule 6: History Must Be Chronological

History events must be ordered by `change_date` ascending.

### Rule 7: First History Event Must Be "none"

The first entry in `history` must have `change_type: "none"` (initial listing).

### Rule 8: Corporate Actions Must Be Chronological

Corporate actions must be ordered by `date` ascending.

### Rule 9: Active Instruments Cannot Have Delisting Date

If `active: true`, `delisting_date` must be `null`.

### Rule 10: Inactive Instruments Must Have Delisting Date

If `active: false`, `delisting_date` must be set.

---

## Wrapper Contributions

### Adding a New Language Wrapper

To add a wrapper for a new language:

1. Create `wrappers/<language>/` directory
2. Implement the standard API (see below)
3. Write tests that match `tests/cross_language_consistency.json`
4. Write a README following the existing pattern
5. Add CI job to `.github/workflows/validate.yml`

### Standard API Contract

All wrappers must implement:

| Method | Description |
|--------|-------------|
| `load(path)` / `new(path)` | Load the registry |
| `count()` / `.count` | Number of instruments |
| `by_isin(isin)` / `byIsin(isin)` | Lookup by ISIN |
| `by_cusip(cusip)` / `byCusip(cusip)` | Lookup by CUSIP |
| `by_figi(figi)` / `byFigi(figi)` | Lookup by FIGI |
| `by_lei(lei)` / `byLei(lei)` | Lookup by LEI |
| `by_ticker(ticker, exchange?)` | Lookup by ticker |
| `by_exchange(exchange)` | Filter by exchange |
| `by_asset_class(class)` | Filter by asset class |
| `by_country(country)` | Filter by country |
| `by_currency(currency)` | Filter by currency |
| `all()` | Return all instruments |
| `meta()` / `version()` | Return metadata |

### Cross-Language Consistency

All wrappers must return identical results for the values in `tests/cross_language_consistency.json`:

```bash
# The consistency contract
cat tests/cross_language_consistency.json
```

---

## Testing Requirements

### Before submitting a PR

Run **all** tests:

```bash
# 1. Registry validation
python3 tools/validate.py --verbose

# 2. Build distribution
python3 tools/build.py

# 3. Python tests (159)
pytest tests/ -v

# 4. JavaScript tests (72)
cd wrappers/javascript && npm test && cd ../..

# 5. Rust tests (19)
cd wrappers/rust && cargo test && cd ../..

# 6. Go tests (42)
cd wrappers/go && go test ./... && cd ../..
```

All must pass with **zero failures**.

---

## Pull Request Process

### Step 1: Fork and branch

```bash
git clone https://github.com/slimissa/asset-identifiers.git
cd asset-identifiers
git checkout -b fix/your-change
```

### Step 2: Make your change

Edit the relevant files.

### Step 3: Validate

Run the full test suite (see above).

### Step 4: Commit

```bash
git add .
git commit -m "Fix: correct AAPL CUSIP check digit"
```

Use clear commit messages:
- `Fix: ...` for corrections
- `Add: ...` for new instruments
- `Update: ...` for changes
- `Remove: ...` for deletions

### Step 5: Push and create PR

```bash
git push origin fix/your-change
```

Then create a Pull Request on GitHub.

### Step 6: Review

A maintainer will:
- Verify the source URL
- Run the CI pipeline
- Check data quality rules
- Review code style

### Step 7: Merge

Once approved and CI passes, the PR is merged.

---

## Style Guidelines

### JSON

- 2-space indentation
- Sorted keys in alphabetical order
- `null` for missing optional fields (not empty strings)
- ISO 8601 dates (`YYYY-MM-DD`)

### Python

- Follow [PEP 8](https://pep8.org/)
- Type hints on all functions
- Docstrings on all public methods

### JavaScript

- Use `const` and `let` (never `var`)
- camelCase for methods
- Semicolons required
- Single quotes for strings

### Rust

- Follow [Rust style guidelines](https://doc.rust-lang.org/1.0.0/style/)
- Use `rustfmt`
- Run `cargo clippy` before submitting

### Go

- Follow [Effective Go](https://go.dev/doc/effective_go)
- Run `go fmt` before submitting
- Use `golint` for linting

---

## Questions?

Open an issue with the `question` label:
https://github.com/slimissa/asset-identifiers/issues/new

---

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

---

## Acknowledgments

Thank you to all contributors who help maintain the quality and accuracy of this registry.
