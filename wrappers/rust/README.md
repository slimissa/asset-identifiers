# Asset Identifiers Registry — Rust Wrapper

A lightweight, dependency-minimal Rust interface to the canonical asset identifier registry.

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
asset-identifiers = "1.0.0"
```

Or install from source:

```bash
git clone https://github.com/slimissa/asset-identifiers.git
cd asset-identifiers/wrappers/rust
cargo build
```

## Quick Start

```rust
use asset_identifiers::{AssetRegistry, AssetClass};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Load the registry
    let registry = AssetRegistry::load("identifiers.json")?;

    // Get instrument count
    println!("Count: {}", registry.count());  // 50

    // Look up by ISIN
    let aapl = registry.by_isin("US0378331005").unwrap();
    println!("Ticker: {}", aapl.ticker);      // AAPL
    println!("Name: {}", aapl.name);          // Apple Inc.
    println!("Currency: {}", aapl.currency);  // USD
    println!("Exchange: {}", aapl.exchange);  // XNAS

    // Look up by CUSIP
    let msft = registry.by_cusip("594918104").unwrap();
    println!("Ticker: {}", msft.ticker);      // MSFT

    // Look up by FIGI
    let aapl_by_figi = registry.by_figi("BBG000B9XRY4").unwrap();
    println!("Name: {}", aapl_by_figi.name);  // Apple Inc.

    // Look up by LEI
    let aapl_by_lei = registry.by_lei("HWUPKR0MPOU8FGXBT394").unwrap();
    println!("Ticker: {}", aapl_by_lei.ticker); // AAPL

    // Look up by ticker on a specific exchange
    let aapl_results = registry.by_ticker("AAPL", Some("XNAS"));
    assert_eq!(aapl_results.len(), 1);
    println!("ISIN: {}", aapl_results[0].isin);  // US0378331005

    // Look up by ticker without exchange (returns Vec for ambiguous tickers)
    let pru_all = registry.by_ticker("PRU", None);
    println!("PRU count: {}", pru_all.len());  // 2

    // Disambiguate by exchange
    let pru_london = registry.by_ticker("PRU", Some("XLON"));
    println!("Name: {}", pru_london[0].name);  // Prudential plc

    let pru_nyse = registry.by_ticker("PRU", Some("XNYS"));
    println!("Name: {}", pru_nyse[0].name);    // Prudential Financial, Inc.

    // Filter by exchange
    let nasdaq = registry.by_exchange("XNAS");
    println!("NASDAQ count: {}", nasdaq.len());

    // Filter by asset class
    let etfs = registry.by_asset_class(AssetClass::Etf);
    println!("ETF count: {}", etfs.len());

    // Filter by country
    let us_instruments = registry.by_country("US");
    println!("US count: {}", us_instruments.len());

    // Filter by currency
    let usd_instruments = registry.by_currency("USD");
    println!("USD count: {}", usd_instruments.len());

    // Get all instruments
    for inst in registry.all() {
        println!("{} ({}): {}", inst.ticker, inst.exchange, inst.isin);
    }

    // Iterate over all instruments
    for inst in &registry {
        println!("{}", inst.ticker);
    }

    // Get registry metadata
    println!("Version: {}", registry.version());    // 1.0.0
    println!("Generated: {}", registry.generated());
    println!("Sources: {:?}", registry.sources());

    // Get aggregate information
    println!("Exchanges: {:?}", registry.exchanges());
    println!("Currencies: {:?}", registry.currencies());
    println!("Countries: {:?}", registry.countries());

    // Check if identifiers exist
    println!("{}", registry.isin_exists("US0378331005"));  // true
    println!("{}", registry.ticker_exists("ZZZZ", None));   // false

    // Get identifier coverage
    let coverage = registry.identifier_coverage();
    println!("ISIN coverage: {:.1}%", coverage.isin.percentage);    // 100.0%
    println!("CUSIP coverage: {:.1}%", coverage.cusip.percentage);  // 86.0%

    // Find ambiguous tickers
    let ambiguous = registry.tickers_with_multiple_listings();
    println!("Ambiguous: {:?}", ambiguous);  // ["PRU"]

    Ok(())
}
```

## API Reference

### Loading

```rust
AssetRegistry::load(path) -> Result<AssetRegistry, RegistryError>
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `P: AsRef<Path>` | Path to `identifiers.json` |

**Errors:**
- `RegistryError::FileRead` — if the file cannot be read
- `RegistryError::InvalidJson` — if the file is not valid JSON
- `RegistryError::DuplicateIdentifier` — if a duplicate ISIN/CUSIP/SEDOL/FIGI/LEI is found

### Properties

| Method | Returns | Description |
|--------|---------|-------------|
| `count()` | `usize` | Number of instruments |
| `path()` | `&Path` | Registry file path |
| `meta()` | `&RegistryMeta` | Full metadata |
| `version()` | `&str` | Registry version |
| `generated()` | `&str` | Generation date |
| `sources()` | `&[String]` | Data sources |

### Lookup Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `by_isin(isin)` | `Option<&Instrument>` | Look up by ISIN |
| `by_cusip(cusip)` | `Option<&Instrument>` | Look up by CUSIP |
| `by_sedol(sedol)` | `Option<&Instrument>` | Look up by SEDOL |
| `by_figi(figi)` | `Option<&Instrument>` | Look up by FIGI |
| `by_lei(lei)` | `Option<&Instrument>` | Look up by LEI |
| `by_ticker(ticker, exchange)` | `Vec<&Instrument>` | Look up by ticker |
| `by_ticker_exchange(ticker, exchange)` | `Option<&Instrument>` | Single-result ticker lookup |

### Filter Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `by_exchange(exchange)` | `Vec<&Instrument>` | All instruments on an exchange |
| `by_asset_class(asset_class)` | `Vec<&Instrument>` | All instruments of an asset class |
| `by_country(country)` | `Vec<&Instrument>` | All instruments from a country |
| `by_currency(currency)` | `Vec<&Instrument>` | All instruments in a currency |

### Bulk Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `all()` | `&[Instrument]` | All instruments as a slice |
| `iter()` | `Iter<Instrument>` | Iterator over all instruments |

### Aggregate Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `exchanges()` | `Vec<&str>` | Sorted MIC codes |
| `asset_classes()` | `Vec<AssetClass>` | Sorted asset classes |
| `currencies()` | `Vec<&str>` | Sorted currency codes |
| `countries()` | `Vec<&str>` | Sorted country codes |

### Convenience Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `isin_exists(isin)` | `bool` | Check ISIN exists |
| `ticker_exists(ticker, exchange)` | `bool` | Check ticker exists |
| `identifier_coverage()` | `IdentifierCoverage` | Coverage statistics |
| `tickers_with_multiple_listings()` | `Vec<&str>` | Ambiguous tickers |

### Iterator Implementation

```rust
// &AssetRegistry implements IntoIterator
for instrument in &registry {
    println!("{}", instrument.ticker);
}
```

### Display Implementation

```rust
println!("{}", registry);
// Output: Asset Identifier Registry v1.0.0 (50 instruments)
```

## Type Safety

The Rust wrapper uses enums for controlled vocabularies:

```rust
pub enum AssetClass {
    Equity,
    Etf,
    Bond,
    Option,
    Future,
    Other,
}

pub enum ListingStatus {
    Primary,
    Secondary,
    DepositaryReceipt,
    Delisted,
}

pub enum CorporateActionType {
    Split,
    ReverseSplit,
    Dividend,
    Spinoff,
    Merger,
    Acquisition,
    RightsIssue,
    Buyback,
}

pub enum ChangeType {
    None,
    Rename,
    Delisting,
    Relisting,
    Merger,
    Acquisition,
    Spinoff,
    Split,
    ReverseSplit,
}
```

This prevents invalid values at compile time — you cannot pass `"crypto"` as an asset class because it is not a valid enum variant.

## Handling Duplicate Tickers

```rust
// PRU exists on both London and New York
let pru_all = registry.by_ticker("PRU", None);
assert_eq!(pru_all.len(), 2);

// Disambiguate by exchange
let pru_london = registry.by_ticker("PRU", Some("XLON"));
assert_eq!(pru_london[0].isin, "GB0007099541");

let pru_nyse = registry.by_ticker("PRU", Some("XNYS"));
assert_eq!(pru_nyse[0].isin, "US7443201022");

// Single-result convenience method
let pru = registry.by_ticker_exchange("PRU", "XLON").unwrap();
assert_eq!(pru.isin, "GB0007099541");
```

## Handling Ticker Changes

```rust
let meta = registry.by_isin("US30303M1027").unwrap();
assert_eq!(meta.ticker, "META");

// History contains the old ticker
for event in &meta.history {
    println!("{} {} {:?}", event.ticker, event.change_date, event.change_type);
}
// Output:
// FB    2012-05-18  None
// META  2022-06-09  Rename

// ISIN never changed
assert_eq!(meta.isin, "US30303M1027");
```

## Multi-Exchange Listings

```rust
let aapl = registry.by_isin("US0378331005").unwrap();

for listing in &aapl.listings {
    println!("{} {} {} {:?}", listing.exchange, listing.ticker, listing.currency, listing.status);
}
// Output:
// XNAS  AAPL  USD  Primary
// XETR  APC   EUR  Secondary
```

## Identifier Coverage

```rust
let coverage = registry.identifier_coverage();

println!("ISIN:  {}/{} ({:.1}%)", coverage.isin.covered, coverage.isin.total, coverage.isin.percentage);
println!("CUSIP: {}/{} ({:.1}%)", coverage.cusip.covered, coverage.cusip.total, coverage.cusip.percentage);
println!("SEDOL: {}/{} ({:.1}%)", coverage.sedol.covered, coverage.sedol.total, coverage.sedol.percentage);
println!("FIGI:  {}/{} ({:.1}%)", coverage.figi.covered, coverage.figi.total, coverage.figi.percentage);
println!("LEI:   {}/{} ({:.1}%)", coverage.lei.covered, coverage.lei.total, coverage.lei.percentage);
```

## Error Handling

All errors use the `thiserror` crate for idiomatic Rust error handling:

```rust
pub enum RegistryError {
    FileRead { path: String, source: std::io::Error },
    InvalidJson { path: String, source: serde_json::Error },
    MissingField { field: &'static str },
    DuplicateIdentifier { identifier_type: &'static str, value: String },
}
```

Example error handling:

```rust
match AssetRegistry::load("identifiers.json") {
    Ok(registry) => println!("Loaded {} instruments", registry.count()),
    Err(RegistryError::FileRead { path, .. }) => eprintln!("File not found: {}", path),
    Err(RegistryError::InvalidJson { path, .. }) => eprintln!("Invalid JSON: {}", path),
    Err(e) => eprintln!("Other error: {}", e),
}
```

## Dependencies

| Crate | Version | Purpose |
|-------|---------|---------|
| `serde` | 1.0 | JSON deserialization with derive |
| `serde_json` | 1.0 | JSON parsing |
| `thiserror` | 1.0 | Idiomatic error types |

## Rust Version Support

- Rust 1.70+ (MSRV)

## Testing

```bash
# Run all tests (unit + doc-tests)
cargo test

# Run only unit tests
cargo test --lib

# Run only doc-tests
cargo test --doc

# Run with release optimizations
cargo test --release
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
- [crates.io](https://crates.io/crates/asset-identifiers)
- [docs.rs](https://docs.rs/asset-identifiers)
```