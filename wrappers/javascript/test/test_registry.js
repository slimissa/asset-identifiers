#!/usr/bin/env node
/**
 * Asset Identifier Registry — JavaScript wrapper tests.
 *
 * Tests cover:
 * - Registry loading
 * - Lookup by all identifier types (ISIN, CUSIP, SEDOL, FIGI, LEI)
 * - Lookup by ticker with and without exchange
 * - Filtering by exchange, asset class, country, currency
 * - Metadata and aggregate information
 * - Convenience methods (resolve, tickerExists, isinExists)
 * - Statistical methods (identifierCoverage, tickersWithMultipleListings)
 * - Iterator support
 * - Duplicate ticker handling
 * - Ticker change history
 * - Multi-exchange listings
 * - Error handling
 * - Cross-language consistency (matches Python wrapper results)
 *
 * Run:
 *   npm test
 *   node --test test/
 */

'use strict';

const { test, describe } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { AssetRegistry } = require('../src/index.js');

// ─── Setup ───────────────────────────────────────────────────────────

const REGISTRY_PATH = path.resolve(__dirname, '../../../identifiers.json');
const registry = new AssetRegistry(REGISTRY_PATH);

// ─── Registry Loading Tests ──────────────────────────────────────────

describe('Registry Loading', () => {
  test('loads successfully', () => {
    assert.ok(registry, 'Registry should be created');
  });

  test('has correct instrument count', () => {
    assert.equal(registry.count, 50);
  });

  test('has instruments array', () => {
    assert.ok(Array.isArray(registry.instruments));
    assert.equal(registry.instruments.length, 50);
  });

  test('has path', () => {
    assert.ok(registry.path.includes('identifiers.json'));
  });

  test('has metadata', () => {
    const meta = registry.meta();
    assert.ok(meta, 'Metadata should exist');
    assert.equal(meta.version, '0.1.0');
    assert.equal(meta.count, 50);
  });
});

// ─── ISIN Lookup Tests ───────────────────────────────────────────────

describe('ISIN Lookup', () => {
  test('finds AAPL by ISIN', () => {
    const aapl = registry.byIsin('US0378331005');
    assert.ok(aapl, 'AAPL should be found');
    assert.equal(aapl.ticker, 'AAPL');
    assert.equal(aapl.name, 'Apple Inc.');
    assert.equal(aapl.currency, 'USD');
    assert.equal(aapl.exchange, 'XNAS');
    assert.equal(aapl.asset_class, 'equity');
  });

  test('finds MSFT by ISIN', () => {
    const msft = registry.byIsin('US5949181045');
    assert.ok(msft);
    assert.equal(msft.ticker, 'MSFT');
  });

  test('finds international instrument by ISIN', () => {
    const sony = registry.byIsin('JP3435000009');
    assert.ok(sony);
    assert.equal(sony.ticker, '7203');
    assert.equal(sony.currency, 'JPY');
  });

  test('returns null for nonexistent ISIN', () => {
    assert.equal(registry.byIsin('XX0000000000'), null);
  });

  test('is case-insensitive', () => {
    const lower = registry.byIsin('us0378331005');
    assert.ok(lower);
    assert.equal(lower.ticker, 'AAPL');
  });
});

// ─── CUSIP Lookup Tests ──────────────────────────────────────────────

describe('CUSIP Lookup', () => {
  test('finds AAPL by CUSIP', () => {
    const aapl = registry.byCusip('037833100');
    assert.ok(aapl);
    assert.equal(aapl.isin, 'US0378331005');
  });

  test('finds MSFT by CUSIP', () => {
    const msft = registry.byCusip('594918104');
    assert.ok(msft);
    assert.equal(msft.ticker, 'MSFT');
  });

  test('returns null for nonexistent CUSIP', () => {
    assert.equal(registry.byCusip('000000000'), null);
  });
});

// ─── FIGI Lookup Tests ───────────────────────────────────────────────

describe('FIGI Lookup', () => {
  test('finds AAPL by FIGI', () => {
    const aapl = registry.byFigi('BBG000B9XRY4');
    assert.ok(aapl);
    assert.equal(aapl.isin, 'US0378331005');
  });

  test('finds META by FIGI', () => {
    const meta = registry.byFigi('BBG000MM2P62');
    assert.ok(meta);
    assert.equal(meta.ticker, 'META');
  });

  test('returns null for nonexistent FIGI', () => {
    assert.equal(registry.byFigi('BBG00000000'), null);
  });
});

// ─── LEI Lookup Tests ────────────────────────────────────────────────

describe('LEI Lookup', () => {
  test('finds AAPL by LEI', () => {
    const aapl = registry.byLei('HWUPKR0MPOU8FGXBT394');
    assert.ok(aapl);
    assert.equal(aapl.ticker, 'AAPL');
  });

  test('returns null for nonexistent LEI', () => {
    assert.equal(registry.byLei('00000000000000000000'), null);
  });
});

// ─── Ticker Lookup Tests ─────────────────────────────────────────────

describe('Ticker Lookup', () => {
  test('finds AAPL by ticker with exchange', () => {
    const aapl = registry.byTicker('AAPL', 'XNAS');
    assert.ok(aapl);
    assert.equal(aapl.isin, 'US0378331005');
  });

  test('finds AAPL by ticker without exchange (returns array)', () => {
    const results = registry.byTicker('AAPL');
    assert.ok(Array.isArray(results));
    assert.equal(results.length, 1);
    assert.equal(results[0].ticker, 'AAPL');
  });

  test('finds PRU on multiple exchanges', () => {
    const pru = registry.byTicker('PRU');
    assert.ok(Array.isArray(pru));
    assert.equal(pru.length, 2);

    const exchanges = pru.map((i) => i.exchange).sort();
    assert.deepEqual(exchanges, ['XLON', 'XNYS']);
  });

  test('disambiguates PRU by exchange', () => {
    const pruLondon = registry.byTicker('PRU', 'XLON');
    assert.equal(pruLondon.isin, 'GB0007099541');
    assert.equal(pruLondon.currency, 'GBP');

    const pruNyse = registry.byTicker('PRU', 'XNYS');
    assert.equal(pruNyse.isin, 'US7443201022');
    assert.equal(pruNyse.currency, 'USD');
  });

  test('returns null for nonexistent ticker with exchange', () => {
    assert.equal(registry.byTicker('ZZZZ', 'XNAS'), null);
  });

  test('returns empty array for nonexistent ticker without exchange', () => {
    assert.deepEqual(registry.byTicker('ZZZZ'), []);
  });

  test('is case-insensitive', () => {
    const aapl = registry.byTicker('aapl', 'xnas');
    assert.ok(aapl);
    assert.equal(aapl.isin, 'US0378331005');
  });
});

// ─── Filtering Tests ─────────────────────────────────────────────────

describe('Filtering', () => {
  test('filters by exchange', () => {
    const xnas = registry.byExchange('XNAS');
    assert.ok(xnas.length > 0);
    for (const inst of xnas) {
      assert.equal(inst.exchange, 'XNAS');
    }
  });

  test('filters by asset class', () => {
    const etfs = registry.byAssetClass('etf');
    assert.ok(etfs.length > 0);
    for (const inst of etfs) {
      assert.equal(inst.asset_class, 'etf');
    }
  });

  test('filters by equity asset class', () => {
    const equities = registry.byAssetClass('equity');
    assert.ok(equities.length > 0);
    assert.equal(equities.length + registry.byAssetClass('etf').length, 50);
  });

  test('filters by country', () => {
    const us = registry.byCountry('US');
    assert.ok(us.length > 0);
    for (const inst of us) {
      assert.equal(inst.country, 'US');
    }
  });

  test('filters by currency', () => {
    const usd = registry.byCurrency('USD');
    assert.ok(usd.length > 0);
    for (const inst of usd) {
      assert.equal(inst.currency, 'USD');
    }
  });

  test('returns empty array for nonexistent exchange', () => {
    assert.deepEqual(registry.byExchange('ZZZZ'), []);
  });
});

// ─── Metadata Tests ──────────────────────────────────────────────────

describe('Metadata', () => {
  test('returns version', () => {
    assert.equal(registry.version(), '0.1.0');
  });

  test('returns generation date', () => {
    assert.ok(registry.generated());
  });

  test('returns sources', () => {
    const sources = registry.sources();
    assert.ok(Array.isArray(sources));
    assert.ok(sources.length >= 1);
  });

  test('returns all instruments', () => {
    const all = registry.all();
    assert.equal(all.length, 50);
  });
});

// ─── Aggregate Information Tests ─────────────────────────────────────

describe('Aggregate Information', () => {
  test('returns sorted exchanges', () => {
    const exchanges = registry.exchanges();
    assert.ok(exchanges.includes('XNAS'));
    assert.ok(exchanges.includes('XNYS'));
    assert.ok(exchanges.includes('XLON'));
    assert.ok(exchanges.includes('XTKS'));
    assert.equal(exchanges.length, 9);
  });

  test('returns sorted asset classes', () => {
    assert.deepEqual(registry.assetClasses(), ['equity', 'etf']);
  });

  test('returns sorted currencies', () => {
    const currencies = registry.currencies();
    assert.ok(currencies.includes('USD'));
    assert.ok(currencies.includes('EUR'));
    assert.ok(currencies.includes('JPY'));
    assert.equal(currencies.length, 7);
  });

  test('returns sorted countries', () => {
    const countries = registry.countries();
    assert.ok(countries.includes('US'));
    assert.ok(countries.includes('GB'));
    assert.ok(countries.includes('JP'));
    assert.equal(countries.length, 8);
  });
});

// ─── Convenience Method Tests ────────────────────────────────────────

describe('Convenience Methods', () => {
  test('tickerExists returns true for existing ticker', () => {
    assert.equal(registry.tickerExists('AAPL'), true);
  });

  test('tickerExists returns false for nonexistent ticker', () => {
    assert.equal(registry.tickerExists('ZZZZ'), false);
  });

  test('tickerExists with exchange', () => {
    assert.equal(registry.tickerExists('PRU', 'XLON'), true);
    assert.equal(registry.tickerExists('PRU', 'ZZZZ'), false);
  });

  test('isinExists returns true for existing ISIN', () => {
    assert.equal(registry.isinExists('US0378331005'), true);
  });

  test('isinExists returns false for nonexistent ISIN', () => {
    assert.equal(registry.isinExists('XX0000000000'), false);
  });

  test('resolve detects ISIN', () => {
    const result = registry.resolve('US0378331005');
    assert.equal(result.ticker, 'AAPL');
  });

  test('resolve detects CUSIP', () => {
    const result = registry.resolve('037833100');
    assert.equal(result.ticker, 'AAPL');
  });

  test('resolve detects FIGI', () => {
    const result = registry.resolve('BBG000B9XRY4');
    assert.equal(result.ticker, 'AAPL');
  });

  test('resolve detects LEI', () => {
    const result = registry.resolve('HWUPKR0MPOU8FGXBT394');
    assert.equal(result.ticker, 'AAPL');
  });

  test('resolve detects ticker', () => {
    const result = registry.resolve('AAPL', 'XNAS');
    assert.equal(result.isin, 'US0378331005');
  });

  test('resolve detects ambiguous ticker', () => {
    const result = registry.resolve('PRU');
    assert.ok(Array.isArray(result));
    assert.equal(result.length, 2);
  });
});

// ─── Statistical Method Tests ────────────────────────────────────────

describe('Statistical Methods', () => {
  test('identifierCoverage returns ISIN coverage', () => {
    const coverage = registry.identifierCoverage();
    assert.equal(coverage.isin.covered, 50);
    assert.equal(coverage.isin.total, 50);
    assert.equal(coverage.isin.percentage, 100);
  });

  test('identifierCoverage returns CUSIP coverage', () => {
    const coverage = registry.identifierCoverage();
    assert.equal(coverage.cusip.covered, 43);
    assert.equal(coverage.cusip.percentage, 86);
  });

  test('identifierCoverage returns SEDOL coverage', () => {
    const coverage = registry.identifierCoverage();
    assert.equal(coverage.sedol.covered, 0);
    assert.equal(coverage.sedol.percentage, 0);
  });

  test('identifierCoverage returns FIGI coverage', () => {
    const coverage = registry.identifierCoverage();
    assert.equal(coverage.figi.covered, 49);
    assert.equal(coverage.figi.percentage, 98);
  });

  test('identifierCoverage returns LEI coverage', () => {
    const coverage = registry.identifierCoverage();
    assert.equal(coverage.lei.covered, 50);
    assert.equal(coverage.lei.percentage, 100);
  });

  test('tickersWithMultipleListings returns PRU', () => {
    const ambiguous = registry.tickersWithMultipleListings();
    assert.ok(ambiguous.includes('PRU'));
  });
});

// ─── Ticker Change Tests ─────────────────────────────────────────────

describe('Ticker Changes', () => {
  test('META history contains FB', () => {
    const meta = registry.byIsin('US30303M1027');
    assert.equal(meta.ticker, 'META');
    const historyTickers = meta.history.map((h) => h.ticker);
    assert.ok(historyTickers.includes('FB'));
    assert.ok(historyTickers.includes('META'));
  });

  test('META change date is correct', () => {
    const meta = registry.byIsin('US30303M1027');
    const renameEvent = meta.history.find((h) => h.change_type === 'rename');
    assert.equal(renameEvent.change_date, '2022-06-09');
  });

  test('META ISIN unchanged after rename', () => {
    const meta = registry.byIsin('US30303M1027');
    assert.equal(meta.isin, 'US30303M1027');
  });

  test('XOM history has initial listing', () => {
    const xom = registry.byTicker('XOM', 'XNYS');
    assert.equal(xom.history[0].change_type, 'none');
    assert.equal(xom.history[0].ticker, 'XON');
  });

  test('XOM history has merger rename', () => {
    const xom = registry.byTicker('XOM', 'XNYS');
    const renameEvent = xom.history.find((h) => h.change_type === 'rename');
    assert.equal(renameEvent.ticker, 'XOM');
    assert.equal(renameEvent.reason, 'MERGER');
  });
});

// ─── Multi-Exchange Listing Tests ────────────────────────────────────

describe('Multi-Exchange Listings', () => {
  test('AAPL has multiple listings', () => {
    const aapl = registry.byIsin('US0378331005');
    assert.ok(aapl.listings.length >= 2);
  });

  test('AAPL listings include XNAS and XETR', () => {
    const aapl = registry.byIsin('US0378331005');
    const exchanges = aapl.listings.map((l) => l.exchange);
    assert.ok(exchanges.includes('XNAS'));
    assert.ok(exchanges.includes('XETR'));
  });

  test('AAPL primary listing is XNAS', () => {
    const aapl = registry.byIsin('US0378331005');
    const primary = aapl.listings.find((l) => l.status === 'PRIMARY');
    assert.equal(primary.exchange, 'XNAS');
  });

  test('AAPL listings have different currencies', () => {
    const aapl = registry.byIsin('US0378331005');
    const currencies = aapl.listings.map((l) => l.currency);
    assert.ok(currencies.includes('USD'));
    assert.ok(currencies.includes('EUR'));
  });
});

// ─── Iterator Tests ──────────────────────────────────────────────────

describe('Iterator', () => {
  test('iterates over all instruments', () => {
    const tickers = [];
    for (const inst of registry) {
      tickers.push(inst.ticker);
    }
    assert.equal(tickers.length, 50);
    assert.ok(tickers.includes('AAPL'));
    assert.ok(tickers.includes('MSFT'));
  });

  test('spread operator works', () => {
    const instruments = [...registry];
    assert.equal(instruments.length, 50);
  });
});

// ─── String Representation Tests ─────────────────────────────────────

describe('String Representation', () => {
  test('toString returns meaningful string', () => {
    const str = registry.toString();
    assert.ok(str.includes('Asset Identifier Registry'));
    assert.ok(str.includes('50'));
  });

  test('toJSON returns object', () => {
    const json = registry.toJSON();
    assert.equal(json.count, 50);
    assert.equal(json.instruments, 50);
  });
});

// ─── Error Handling Tests ────────────────────────────────────────────

describe('Error Handling', () => {
  test('throws on nonexistent file', () => {
    assert.throws(() => {
      new AssetRegistry('/nonexistent/path/identifiers.json');
    }, /Failed to read registry file/);
  });

  test('throws on invalid JSON', () => {
    const fs = require('fs');
    const os = require('os');
    const invalidPath = path.join(os.tmpdir(), 'invalid_registry.json');
    fs.writeFileSync(invalidPath, '{ invalid json');

    assert.throws(() => {
      new AssetRegistry(invalidPath);
    }, /Invalid JSON/);

    fs.unlinkSync(invalidPath);
  });
});

// ─── Cross-Language Consistency Tests ────────────────────────────────

describe('Cross-Language Consistency', () => {
  test('matches consistency file values', () => {
    const consistencyPath = path.resolve(__dirname, '../../../tests/cross_language_consistency.json');
    const fs = require('fs');
    const consistency = JSON.parse(fs.readFileSync(consistencyPath, 'utf8'));

    // Count matches
    assert.equal(registry.count, consistency.registry.count);

    // AAPL matches
    const aapl = registry.byIsin('US0378331005');
    assert.equal(aapl.ticker, consistency.instruments.aapl.ticker);
    assert.equal(aapl.cusip, consistency.instruments.aapl.cusip);
    assert.equal(aapl.figi, consistency.instruments.aapl.figi);

    // META matches
    const meta = registry.byIsin('US30303M1027');
    assert.equal(meta.ticker, consistency.instruments.meta.ticker);

    // PRU matches
    const pru = registry.byTicker('PRU');
    assert.equal(pru.length, consistency.instruments.pru.count);
  });
});
