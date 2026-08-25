# Asset Identifiers Registry — Go Wrapper

A lightweight, dependency-free Go interface to the canonical asset identifier registry.

## Installation

```bash
go get github.com/slimissa/asset-identifiers-go
```

Or install from source:

```bash
git clone https://github.com/slimissa/asset-identifiers.git
cd asset-identifiers/wrappers/go
go build ./...
```

## Quick Start

```go
package main

import (
    "fmt"
    "log"

    assetidentifiers "github.com/slimissa/asset-identifiers-go"
)

func main() {
    // Load the registry
    registry, err := assetidentifiers.LoadRegistry("identifiers.json")
    if err != nil {
        log.Fatal(err)
    }

    // Get instrument count
    fmt.Println("Count:", registry.Count())  // 50

    // Look up by ISIN
    aapl, ok := registry.ByIsin("US0378331005")
    if ok {
        fmt.Println("Ticker:", aapl.Ticker)      // AAPL
        fmt.Println("Name:", aapl.Name)          // Apple Inc.
        fmt.Println("Currency:", aapl.Currency)  // USD
        fmt.Println("Exchange:", aapl.Exchange)  // XNAS
    }

    // Look up by CUSIP
    msft, ok := registry.ByCusip("594918104")
    if ok {
        fmt.Println("Ticker:", msft.Ticker)  // MSFT
    }

    // Look up by FIGI
    aaplByFigi, ok := registry.ByFigi("BBG000B9XRY4")
    if ok {
        fmt.Println("Name:", aaplByFigi.Name)  // Apple Inc.
    }

    // Look up by LEI
    aaplByLei, ok := registry.ByLei("HWUPKR0MPOU8FGXBT394")
    if ok {
        fmt.Println("Ticker:", aaplByLei.Ticker)  // AAPL
    }

    // Look up by ticker on a specific exchange
    aaplResults := registry.ByTicker("AAPL", "XNAS")
    if len(aaplResults) == 1 {
        fmt.Println("ISIN:", aaplResults[0].Isin)  // US0378331005
    }

    // Look up by ticker without exchange (returns slice for ambiguous tickers)
    pruAll := registry.ByTicker("PRU", "")
    fmt.Println("PRU count:", len(pruAll))  // 2

    // Disambiguate by exchange
    pruLondon := registry.ByTicker("PRU", "XLON")
    if len(pruLondon) == 1 {
        fmt.Println("Name:", pruLondon[0].Name)  // Prudential plc
    }

    pruNyse := registry.ByTicker("PRU", "XNYS")
    if len(pruNyse) == 1 {
        fmt.Println("Name:", pruNyse[0].Name)  // Prudential Financial, Inc.
    }

    // Convenience method for single-result ticker lookup
    pru, ok := registry.ByTickerExchange("PRU", "XLON")
    if ok {
        fmt.Println("ISIN:", pru.Isin)  // GB0007099541
    }

    // Filter by exchange
    nasdaq := registry.ByExchange("XNAS")
    fmt.Println("NASDAQ count:", len(nasdaq))

    // Filter by asset class
    etfs := registry.ByAssetClass(assetidentifiers.AssetClassEtf)
    fmt.Println("ETF count:", len(etfs))

    // Filter by country
    usInstruments := registry.ByCountry("US")
    fmt.Println("US count:", len(usInstruments))

    // Filter by currency
    usdInstruments := registry.ByCurrency("USD")
    fmt.Println("USD count:", len(usdInstruments))

    // Get all instruments
    for _, inst := range registry.All() {
        fmt.Printf("%s (%s): %s\n", inst.Ticker, inst.Exchange, inst.Isin)
    }

    // Get registry metadata
    fmt.Println("Version:", registry.Version())    // 1.0.0
    fmt.Println("Generated:", registry.Generated())
    fmt.Println("Sources:", registry.Sources())

    // Get aggregate information
    fmt.Println("Exchanges:", registry.Exchanges())
    fmt.Println("Currencies:", registry.Currencies())
    fmt.Println("Countries:", registry.Countries())

    // Check if identifiers exist
    fmt.Println(registry.IsinExists("US0378331005"))   // true
    fmt.Println(registry.TickerExists("ZZZZ", ""))     // false

    // Get identifier coverage
    coverage := registry.IdentifierCoverage()
    fmt.Printf("ISIN: %d/%d (%.1f%%)\n", coverage.Isin.Covered, coverage.Isin.Total, coverage.Isin.Percentage)
    fmt.Printf("CUSIP: %d/%d (%.1f%%)\n", coverage.Cusip.Covered, coverage.Cusip.Total, coverage.Cusip.Percentage)

    // Find ambiguous tickers
    ambiguous := registry.TickersWithMultipleListings()
    fmt.Println("Ambiguous:", ambiguous)  // [PRU]

    // String representation
    fmt.Println(registry)  // Asset Identifier Registry v1.0.0 (50 instruments)
}
```

## API Reference

### Loading

```go
LoadRegistry(path string) (*AssetRegistry, error)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `string` | Path to `identifiers.json` |

**Errors:**
- `*RegistryError` with `Op: "read file"` — if file cannot be read
- `*RegistryError` with `Op: "parse JSON"` — if file is not valid JSON
- `*RegistryError` with `Op: "duplicate ISIN"` — if duplicate ISIN found
- `*RegistryError` with `Op: "duplicate CUSIP"` — if duplicate CUSIP found
- `*RegistryError` with `Op: "duplicate SEDOL"` — if duplicate SEDOL found
- `*RegistryError` with `Op: "duplicate FIGI"` — if duplicate FIGI found
- `*RegistryError` with `Op: "duplicate LEI"` — if duplicate LEI found

### Properties

| Method | Returns | Description |
|--------|---------|-------------|
| `Count()` | `int` | Number of instruments |
| `Path()` | `string` | Absolute path to registry file |
| `Meta()` | `*RegistryMeta` | Full metadata |
| `Version()` | `string` | Registry version |
| `Generated()` | `string` | Generation date |
| `Sources()` | `[]string` | Data sources |

### Lookup Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `ByIsin(isin)` | `(*Instrument, bool)` | Look up by ISIN |
| `ByCusip(cusip)` | `(*Instrument, bool)` | Look up by CUSIP |
| `BySedol(sedol)` | `(*Instrument, bool)` | Look up by SEDOL |
| `ByFigi(figi)` | `(*Instrument, bool)` | Look up by FIGI |
| `ByLei(lei)` | `(*Instrument, bool)` | Look up by LEI |
| `ByTicker(ticker, exchange)` | `[]*Instrument` | Look up by ticker |
| `ByTickerExchange(ticker, exchange)` | `(*Instrument, bool)` | Single-result ticker lookup |

### Filter Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `ByExchange(exchange)` | `[]*Instrument` | All instruments on an exchange |
| `ByAssetClass(assetClass)` | `[]*Instrument` | All instruments of an asset class |
| `ByCountry(country)` | `[]*Instrument` | All instruments from a country |
| `ByCurrency(currency)` | `[]*Instrument` | All instruments in a currency |

### Bulk Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `All()` | `[]Instrument` | All instruments (copy) |
| `Instruments()` | `*[]Instrument` | Pointer to instruments slice |

### Aggregate Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `Exchanges()` | `[]string` | Sorted MIC codes |
| `AssetClasses()` | `[]AssetClass` | Sorted asset classes |
| `Currencies()` | `[]string` | Sorted currency codes |
| `Countries()` | `[]string` | Sorted country codes |

### Convenience Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `IsinExists(isin)` | `bool` | Check ISIN exists |
| `TickerExists(ticker, exchange)` | `bool` | Check ticker exists |
| `IdentifierCoverage()` | `IdentifierCoverage` | Coverage statistics |
| `TickersWithMultipleListings()` | `[]string` | Ambiguous tickers |

### String Representation

```go
// fmt.Stringer interface
fmt.Println(registry)
// Output: Asset Identifier Registry v1.0.0 (50 instruments)
```

## Type Safety

The Go wrapper uses typed string constants for controlled vocabularies:

```go
// Asset classes
const (
    AssetClassEquity AssetClass = "equity"
    AssetClassEtf    AssetClass = "etf"
    AssetClassBond   AssetClass = "bond"
    AssetClassOption AssetClass = "option"
    AssetClassFuture AssetClass = "future"
    AssetClassOther  AssetClass = "other"
)

// Listing statuses
const (
    ListingStatusPrimary          ListingStatus = "PRIMARY"
    ListingStatusSecondary        ListingStatus = "SECONDARY"
    ListingStatusDepositaryReceipt ListingStatus = "DEPOSITARY_RECEIPT"
    ListingStatusDelisted         ListingStatus = "DELISTED"
)

// Corporate action types
const (
    CorporateActionSplit        CorporateActionType = "SPLIT"
    CorporateActionReverseSplit CorporateActionType = "REVERSE_SPLIT"
    CorporateActionDividend     CorporateActionType = "DIVIDEND"
    CorporateActionSpinoff      CorporateActionType = "SPINOFF"
    CorporateActionMerger       CorporateActionType = "MERGER"
    CorporateActionAcquisition  CorporateActionType = "ACQUISITION"
    CorporateActionRightsIssue  CorporateActionType = "RIGHTS_ISSUE"
    CorporateActionBuyback      CorporateActionType = "BUYBACK"
)
```

## Handling Duplicate Tickers

```go
// PRU exists on both London and New York
pruAll := registry.ByTicker("PRU", "")
fmt.Println(len(pruAll))  // 2

// Disambiguate by exchange
pruLondon := registry.ByTicker("PRU", "XLON")
fmt.Println(pruLondon[0].Isin)  // GB0007099541

pruNyse := registry.ByTicker("PRU", "XNYS")
fmt.Println(pruNyse[0].Isin)  // US7443201022

// Single-result convenience
pru, ok := registry.ByTickerExchange("PRU", "XLON")
if ok {
    fmt.Println(pru.Isin)  // GB0007099541
}
```

## Handling Ticker Changes

```go
meta, _ := registry.ByIsin("US30303M1027")
fmt.Println(meta.Ticker)  // META

// History contains the old ticker
for _, event := range meta.History {
    fmt.Println(event.Ticker, event.ChangeDate, event.ChangeType)
}
// Output:
// FB    2012-05-18  none
// META  2022-06-09  rename

// ISIN never changed
fmt.Println(meta.Isin)  // US30303M1027
```

## Multi-Exchange Listings

```go
aapl, _ := registry.ByIsin("US0378331005")

for _, listing := range aapl.Listings {
    fmt.Println(listing.Exchange, listing.Ticker, listing.Currency, listing.Status)
}
// Output:
// XNAS  AAPL  USD  PRIMARY
// XETR  APC   EUR  SECONDARY
```

## Identifier Coverage

```go
coverage := registry.IdentifierCoverage()

fmt.Printf("ISIN:  %d/%d (%.1f%%)\n", coverage.Isin.Covered, coverage.Isin.Total, coverage.Isin.Percentage)
fmt.Printf("CUSIP: %d/%d (%.1f%%)\n", coverage.Cusip.Covered, coverage.Cusip.Total, coverage.Cusip.Percentage)
fmt.Printf("SEDOL: %d/%d (%.1f%%)\n", coverage.Sedol.Covered, coverage.Sedol.Total, coverage.Sedol.Percentage)
fmt.Printf("FIGI:  %d/%d (%.1f%%)\n", coverage.Figi.Covered, coverage.Figi.Total, coverage.Figi.Percentage)
fmt.Printf("LEI:   %d/%d (%.1f%%)\n", coverage.Lei.Covered, coverage.Lei.Total, coverage.Lei.Percentage)
```

## Error Handling

```go
registry, err := assetidentifiers.LoadRegistry("identifiers.json")
if err != nil {
    switch e := err.(type) {
    case *assetidentifiers.RegistryError:
        fmt.Println("Operation:", e.Op)
        fmt.Println("Underlying:", e.Unwrap())
    default:
        fmt.Println("Unknown error:", err)
    }
    return
}
```

## Dependencies

None. This wrapper uses only the Go standard library:
- `encoding/json`
- `fmt`
- `os`
- `path/filepath`
- `sort`
- `strings`

## Go Version Support

- Go 1.21+
- Go 1.22+
- Go 1.23+

## Testing

```bash
# Run all tests
go test ./...

# Run with verbose output
go test ./... -v

# Run with coverage
go test ./... -cover

# Run with race detector
go test ./... -race
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
- [Go Package Registry](https://pkg.go.dev/github.com/slimissa/asset-identifiers-go)
```