# Asset Identifiers Registry — JavaScript Wrapper

A lightweight, dependency-free JavaScript interface to the canonical asset identifier registry.

## Installation

```bash
npm install asset-identifiers-registry
```

Or install from source:

```bash
git clone https://github.com/slimissa/asset-identifiers.git
cd asset-identifiers/wrappers/javascript
npm install
```

## Quick Start

```javascript
const { AssetRegistry } = require('asset-identifiers-registry');

// Load the registry
const registry = new AssetRegistry('identifiers.json');

// Get instrument count
console.log(registry.count);  // 50

// Look up by ISIN
const aapl = registry.byIsin('US0378331005');
console.log(aapl.ticker);      // AAPL
console.log(aapl.name);        // Apple Inc.
console.log(aapl.currency);    // USD
console.log(aapl.exchange);    // XNAS

// Look up by CUSIP
const msft = registry.byCusip('594918104');
console.log(msft.ticker);      // MSFT

// Look up by FIGI
const aaplByFigi = registry.byFigi('BBG000B9XRY4');
console.log(aaplByFigi.name);  // Apple Inc.

// Look up by LEI
const aaplByLei = registry.byLei('HWUPKR0MPOU8FGXBT394');
console.log(aaplByLei.ticker); // AAPL

// Look up by ticker on a specific exchange
const aaplTicker = registry.byTicker('AAPL', 'XNAS');
console.log(aaplTicker.isin);  // US0378331005

// Look up by ticker without exchange (returns array for ambiguous tickers)
const pruAll = registry.byTicker('PRU');
console.log(pruAll.length);    // 2

// Disambiguate by exchange
const pruLondon = registry.byTicker('PRU', 'XLON');
console.log(pruLondon.name);   // Prudential plc

const pruNyse = registry.byTicker('PRU', 'XNYS');
console.log(pruNyse.name);     // Prudential Financial, Inc.

// Filter by exchange
const nasdaq = registry.byExchange('XNAS');
console.log(nasdaq.length);

// Filter by asset class
const etfs = registry.byAssetClass('etf');
console.log(etfs.length);

// Filter by country
const usInstruments = registry.byCountry('US');
console.log(usInstruments.length);

// Filter by currency
const usdInstruments = registry.byCurrency('USD');
console.log(usdInstruments.length);

// Get all instruments
const all = registry.all();
for (const inst of all) {
  console.log(`${inst.ticker} (${inst.exchange}): ${inst.isin}`);
}

// Get registry metadata
const meta = registry.meta();
console.log(meta.version);     // 0.1.0
console.log(meta.count);       // 50

// Get aggregate information
console.log(registry.exchanges());      // ['XETR', 'XHKG', ...]
console.log(registry.assetClasses());   // ['equity', 'etf']
console.log(registry.currencies());     // ['CHF', 'EUR', ...]
console.log(registry.countries());      // ['CH', 'DE', ...]

// Check if identifiers exist
console.log(registry.isinExists('US0378331005'));   // true
console.log(registry.tickerExists('ZZZZ'));          // false

// Auto-detect identifier type with resolve()
registry.resolve('US0378331005');     // Detects ISIN
registry.resolve('037833100');        // Detects CUSIP
registry.resolve('AAPL', 'XNAS');     // Detects ticker
registry.resolve('BBG000B9XRY4');     // Detects FIGI

// Get identifier coverage statistics
const coverage = registry.identifierCoverage();
console.log(coverage.isin.percentage);    // 100
console.log(coverage.cusip.percentage);   // 86

// Find tickers with multiple exchange listings
const ambiguous = registry.tickersWithMultipleListings();
console.log(ambiguous);  // ['PRU']

// Iterate over all instruments
for (const instrument of registry) {
  console.log(instrument.ticker);
}

// Spread operator
const tickers = [...registry].map(i => i.ticker);
console.log(tickers.length);  // 50
```

## API Reference

### Constructor

```javascript
new AssetRegistry(path)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `string` | Path to `identifiers.json` (default: `"identifiers.json"`) |

**Throws:**
- `Error` with message `"Failed to read registry file: ..."` if the path does not exist
- `Error` with message `"Invalid JSON in registry file: ..."` if the file is not valid JSON

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `count` | `number` | Number of instruments |
| `instruments` | `Object[]` | All instrument objects |
| `path` | `string` | Registry file path |

### Lookup Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `byIsin(isin)` | `Object \| null` | Look up by ISIN |
| `byCusip(cusip)` | `Object \| null` | Look up by CUSIP |
| `bySedol(sedol)` | `Object \| null` | Look up by SEDOL |
| `byFigi(figi)` | `Object \| null` | Look up by FIGI |
| `byLei(lei)` | `Object \| null` | Look up by LEI |
| `byTicker(ticker, exchange?)` | `Object \| Object[] \| null` | Look up by ticker |

### Filter Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `byExchange(exchange)` | `Object[]` | All instruments on an exchange |
| `byAssetClass(assetClass)` | `Object[]` | All instruments of an asset class |
| `byCountry(country)` | `Object[]` | All instruments from a country |
| `byCurrency(currency)` | `Object[]` | All instruments in a currency |

### Bulk Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `all()` | `Object[]` | All instruments |

### Metadata Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `meta()` | `Object` | Full metadata |
| `version()` | `string` | Registry version |
| `generated()` | `string` | Generation date |
| `sources()` | `string[]` | Data sources |

### Aggregate Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `exchanges()` | `string[]` | Sorted MIC codes |
| `assetClasses()` | `string[]` | Sorted asset classes |
| `currencies()` | `string[]` | Sorted currency codes |
| `countries()` | `string[]` | Sorted country codes |

### Convenience Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `resolve(identifier, exchange?)` | `Object \| Object[] \| null` | Auto-detect identifier type |
| `tickerExists(ticker, exchange?)` | `boolean` | Check ticker exists |
| `isinExists(isin)` | `boolean` | Check ISIN exists |
| `identifierCoverage()` | `Object` | Coverage statistics |
| `tickersWithMultipleListings()` | `string[]` | Ambiguous tickers |

### Iterator and Representation

| Method/Property | Description |
|-----------------|-------------|
| `[Symbol.iterator]()` | Iterates over all instruments |
| `toString()` | Human-readable representation |
| `toJSON()` | JSON serialization |

## TypeScript Support

The package includes full TypeScript type definitions.

```typescript
import { AssetRegistry, Instrument } from 'asset-identifiers-registry';

const registry = new AssetRegistry('identifiers.json');

// TypeScript knows the return type
const aapl: Instrument | null = registry.byIsin('US0378331005');
if (aapl) {
  console.log(aapl.ticker);  // Type-safe access
}

// TypeScript catches errors at compile time
// registry.byIsin(123);        // Error: argument must be string
// registry.byExchange();        // Error: missing argument
```

## Handling Duplicate Tickers

Some tickers are ambiguous — the same symbol exists on multiple exchanges.

```javascript
// PRU exists on both London and New York
const pru = registry.byTicker('PRU');
// Returns array with 2 items

// Disambiguate by exchange
const london = registry.byTicker('PRU', 'XLON');   // Single object
const newYork = registry.byTicker('PRU', 'XNYS');  // Single object

// Check if a ticker is ambiguous
const ambiguous = registry.tickersWithMultipleListings();
console.log(ambiguous);  // ['PRU']
```

## Handling Ticker Changes

The registry preserves historical ticker changes. The ISIN remains permanent even when the ticker changes.

```javascript
// Meta Platforms changed from FB to META in 2022
const meta = registry.byIsin('US30303M1027');
console.log(meta.ticker);  // META

// History contains the old ticker
for (const event of meta.history) {
  console.log(event.ticker, event.change_date, event.change_type);
}
// Output:
// FB    2012-05-18  none
// META  2022-06-09  rename

// The ISIN never changed
console.log(meta.isin);  // US30303M1027
```

## Multi-Exchange Listings

Some instruments are listed on multiple exchanges.

```javascript
const aapl = registry.byIsin('US0378331005');

for (const listing of aapl.listings) {
  console.log(listing.exchange, listing.ticker, listing.currency, listing.status);
}
// Output:
// XNAS  AAPL  USD  PRIMARY
// XETR  APC   EUR  SECONDARY
```

## Identifier Coverage

```javascript
const coverage = registry.identifierCoverage();

for (const [type, stats] of Object.entries(coverage)) {
  console.log(`${type.toUpperCase()}: ${stats.covered}/${stats.total} (${stats.percentage}%)`);
}

// Output:
// ISIN:  50/50 (100%)
// CUSIP: 43/50 (86%)
// SEDOL: 0/50 (0%)
// FIGI:  49/50 (98%)
// LEI:   50/50 (100%)
```

## Dependencies

None. This wrapper uses only the Node.js standard library (`fs`, `path`).

## Node.js Version Support

- Node.js 14+
- Node.js 16+
- Node.js 18+
- Node.js 20+
- Node.js 22+

## Testing

```bash
# Run all tests
npm test

# Run with coverage
node --test --experimental-test-coverage test/
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
