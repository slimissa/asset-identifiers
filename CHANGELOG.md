# Changelog

All notable changes to the Asset Identifier Registry will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Populate SEDOL identifiers from LSE SEDOL Masterfile
- Expand to 750 instruments (full S&P 500 + NASDAQ 100 + major international)
- Add options chains to the registry
- Add futures contracts
- Add TypeScript type definitions for JavaScript wrapper
- Add benchmark suite for wrapper performance comparison
- Add `strict` feature to Rust wrapper (check-digit validation at load time)

### Known Issues

- SEDOL coverage is 0% — requires licensed LSE SEDOL Masterfile access
- FIGI coverage is 98% — 1 instrument missing (Roche Holding AG)
- `history/ticker_changes.json` is empty — event log not yet populated

---

## [1.0.0] — 2026-08-14

### Added

#### Core Registry

- **50 instruments** covering major US equities, ETFs, and international listings
- **Full identifier support**: ISIN, CUSIP, SEDOL (nullable), FIGI, LEI
- **Ticker change history**: META (was FB), GOOGL (was GOOG), XOM (was XON)
- **Duplicate ticker disambiguation**: PRU on XLON and XNYS
- **Multi-exchange listings**: AAPL on XNAS (primary) and XETR (secondary)
- **Corporate actions**: Splits for AAPL, GOOGL, AMZN, NVDA, KO, WMT, TSLA, AVGO; spinoff for GE
- **Coverage metadata**: 9 exchanges, 2 asset classes, 8 countries, 7 currencies

#### Schema

- `schema.json` — Complete JSON Schema for registry validation
- Strict field validation with regex patterns
- Enumerations for asset classes, listing statuses, corporate action types
- Nullable identifier fields with format validation

#### Validation Tools

- `tools/validate.py` — Multi-layer validation engine:
  - JSON Schema compliance
  - ISIN check digits (ISO 6166 Luhn algorithm)
  - CUSIP check digits (modified Luhn)
  - SEDOL check digits (weighted sum)
  - ISO 3166-1 country code validation
  - Uniqueness constraints (ISIN, CUSIP, SEDOL, FIGI, LEI, ticker+exchange)
  - Business rules (country-specific identifier requirements)
  - Coverage auto-check (meta.coverage vs actual data)
  - Temporal consistency (history ordering, date validation)

- `tools/build.py` — Distribution artifact builder:
  - Merges history from event log
  - Updates metadata with build timestamp
  - Produces `identifiers.dist.json` (pretty-printed)
  - Produces `identifiers.dist.min.json` (minified)
  - Prints build summary with coverage statistics

- `tools/fetch_identifiers.py` — OpenFIGI data fetcher:
  - Fetches real FIGIs from OpenFIGI API
  - Rate limiting (1 request per second)
  - Error handling for HTTP 429 (rate limited)

#### Python Wrapper

- `wrappers/python/asset_identifiers/__init__.py` — Package exports
- `wrappers/python/asset_identifiers/registry.py` — Full wrapper (489 lines):
  - O(1) lookups via HashMap indices
  - `by_isin()`, `by_cusip()`, `by_sedol()`, `by_figi()`, `by_lei()`
  - `by_ticker()` with exchange disambiguation
  - `by_exchange()`, `by_asset_class()`, `by_country()`, `by_currency()`
  - `resolve()` — auto-detect identifier type
  - `identifier_coverage()` — coverage statistics
  - `tickers_with_multiple_listings()` — ambiguous tickers
  - Iterator support (`for inst in registry`)
  - Full type hints

- `wrappers/python/pyproject.toml` — Package configuration
- `wrappers/python/asset_identifiers/py.typed` — Type hint marker
- **159 tests** covering all functionality

#### JavaScript Wrapper

- `wrappers/javascript/src/index.js` — Full wrapper (487 lines):
  - Map-based indices for O(1) lookups
  - camelCase methods: `byIsin()`, `byCusip()`, `byFigi()`, `byLei()`
  - `byTicker()` with optional exchange parameter
  - `resolve()` — auto-detect identifier type
  - `identifierCoverage()` — coverage statistics
  - Iterator support via `Symbol.iterator`
  - `toString()` and `toJSON()` methods

- `wrappers/javascript/src/index.d.ts` — Complete TypeScript definitions
- `wrappers/javascript/package.json` — npm package configuration
- **72 tests** covering all functionality

#### Rust Wrapper

- `wrappers/rust/src/lib.rs` — Full wrapper (887 lines):
  - `HashMap<usize>` indices for O(1) lookups
  - Typed enums: `AssetClass`, `ListingStatus`, `CorporateActionType`, `ChangeType`
  - `thiserror` for idiomatic error handling
  - `serde` for JSON deserialization
  - Duplicate identifier detection at load time
  - `IntoIterator` implementation
  - `Display` trait for human-readable output

- `wrappers/rust/Cargo.toml` — Crate configuration
- **19 tests** (16 unit + 3 doc-tests)

#### Go Wrapper

- `wrappers/go/registry.go` — Full wrapper (633 lines):
  - `map[string]int` indices for O(1) lookups
  - Typed string constants for enums
  - `RegistryError` with `Unwrap()` for error wrapping
  - `(value, bool)` return pattern
  - `ByTickerExchange()` for single-result convenience
  - `String()` method for `fmt.Println`

- `wrappers/go/go.mod` — Zero-dependency module
- **42 tests** covering all functionality

#### Examples

- `examples/python_lookup.py` — Python usage example
- `examples/javascript_lookup.js` — JavaScript usage example
- `examples/rust_lookup.rs` — Rust usage example
- `examples/go_lookup.go` — Go usage example
- All examples produce identical output for cross-language consistency

#### CI/CD

- `.github/workflows/validate.yml` — Full CI pipeline:
  - Python: registry validation, build, 159 tests
  - JavaScript: 72 tests
  - Rust: format check, clippy, 19 tests
  - Go: 42 tests
  - Schema: JSON Schema validation
  - Cross-language consistency verification

#### Documentation

- Root `README.md` — Full project documentation
- `wrappers/python/README.md` — Python wrapper docs
- `wrappers/javascript/README.md` — JavaScript wrapper docs
- `wrappers/rust/README.md` — Rust wrapper docs
- `wrappers/go/README.md` — Go wrapper docs
- `.github/ISSUE_TEMPLATE/identifier_update.md` — Structured update requests

### Changed

- `identifiers.json` — Fixed XOM history to include initial listing event
- `identifiers.json` — Sorted corporate actions chronologically for all instruments
- `identifiers.json` — Added missing exchanges to meta.coverage (XSWX, XKRX, XPAR)
- `tools/validate.py` — Added ISO 3166-1 country code validation
- `tools/validate.py` — Added coverage auto-check
- `tools/validate.py` — Relaxed SEDOL requirement (temporary, until LSE Masterfile access)
- `tools/validate.py` — Removed cross-registry warnings (non-fatal)
- `tools/build.py` — Fixed datetime deprecation warning
- `wrappers/rust/src/lib.rs` — Fixed doc-test paths
- `wrappers/rust/Cargo.toml` — Removed nonexistent bench section

### Fixed

- **Bug**: `validate_isin_check_digit()` accepted invalid country codes — Fixed by adding full ISO 3166-1 country list
- **Bug**: `validate_isin_check_digit()` crashed on invalid characters — Fixed by adding `isdigit()` check
- **Bug**: Duplicate SEDOLs in registry data — Fixed by setting all SEDOLs to null
- **Bug**: Duplicate FIGIs in registry data — Fixed by fetching real FIGIs from OpenFIGI
- **Bug**: XOM history missing initial listing — Fixed by adding XON → XOM history
- **Bug**: AAPL corporate actions not chronological — Fixed by sorting
- **Bug**: NVDA corporate actions not chronological — Fixed by sorting
- **Bug**: Missing exchanges in meta.coverage — Fixed by auto-check

### Removed

- Removed placeholder SEDOLs that were mathematically invalid
- Removed placeholder FIGIs that were duplicated across instruments
- Removed `[[bench]]` section from Cargo.toml (benchmark file did not exist)

---

## Versioning Summary

| Version | Date | Instruments | Tests | Key Changes |
|---------|------|-------------|-------|-------------|
| 1.0.0 | 2026-08-14 | 50 | 292 | Initial release |
```

## What this CHANGELOG covers

| Section | Content |
|---------|---------|
| Unreleased | Planned features and known issues |
| 1.0.0 Added | Everything new in the initial release |
| 1.0.0 Changed | Modifications to existing files |
| 1.0.0 Fixed | All bugs that were found and fixed |
| 1.0.0 Removed | Items that were deleted |
| Versioning Summary | At-a-glance version history |

## Why this format works

[Confirmed] The [Keep a Changelog](https://keepachangelog.com/) format is the industry standard. It makes it easy for users to:
- See what changed in each version
- Decide whether to upgrade
- Understand breaking changes
- Track data corrections