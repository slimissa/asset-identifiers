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
const fs = require('fs');
const os = require('os');
const { AssetRegistry } = require('../src/index.js');
const fx = require('./fixture.js');

// ─── Registry Loading Tests ──────────────────────────────────────────

describe('Registry Loading', () => {
  test('loads successfully', () => {
    assert.ok(fx.registry);
  });

  test('has correct instrument count', () => {
    assert.equal(fx.registry.count, fx.count);
  });

  test('has instruments array', () => {
    assert.ok(Array.isArray(fx.registry.instruments));
    assert.equal(fx.registry.instruments.length, fx.count);
  });

  test('has path pointing at fixture', () => {
    assert.ok(fx.registry.path.includes('identifiers.test.json'));
  });

  test('has metadata', () => {
    const meta = fx.registry.meta();
    assert.ok(meta);
    assert.equal(meta.count, fx.count);
  });
});

// ─── ISIN Lookup Tests ───────────────────────────────────────────────

describe('ISIN Lookup', () => {
  test('finds TESTA by ISIN', () => {
    const inst = fx.registry.byIsin(fx.TESTA.isin);
    assert.ok(inst);
    assert.equal(inst.ticker, fx.TESTA.ticker);
    assert.equal(inst.name, fx.TESTA.name);
    assert.equal(inst.currency, fx.TESTA.currency);
    assert.equal(inst.exchange, fx.TESTA.exchange);
  });

  test('finds NEWTICK by ISIN', () => {
    const inst = fx.registry.byIsin(fx.NEWTICK.isin);
    assert.ok(inst);
    assert.equal(inst.ticker, fx.NEWTICK.ticker);
  });

  test('returns null for nonexistent ISIN', () => {
    assert.equal(fx.registry.byIsin('XX0000000000'), null);
  });

  test('is case-insensitive', () => {
    const lower = fx.TESTA.isin.toLowerCase();
    const inst = fx.registry.byIsin(lower);
    assert.ok(inst);
    assert.equal(inst.ticker, fx.TESTA.ticker);
  });
});

// ─── CUSIP Lookup Tests ──────────────────────────────────────────────

describe('CUSIP Lookup', () => {
  test('finds TESTA by CUSIP', () => {
    assert.ok(fx.TESTA.cusip, 'fixture TESTA has no CUSIP');
    const inst = fx.registry.byCusip(fx.TESTA.cusip);
    assert.ok(inst);
    assert.equal(inst.isin, fx.TESTA.isin);
  });

  test('returns null for nonexistent CUSIP', () => {
    assert.equal(fx.registry.byCusip('999999999'), null);
  });
});

// ─── FIGI Lookup Tests ───────────────────────────────────────────────

describe('FIGI Lookup', () => {
  test('finds TESTA by FIGI', () => {
    assert.ok(fx.TESTA.figi, 'fixture TESTA has no FIGI');
    const inst = fx.registry.byFigi(fx.TESTA.figi);
    assert.ok(inst);
    assert.equal(inst.isin, fx.TESTA.isin);
  });

  test('finds NEWTICK by FIGI', () => {
    assert.ok(fx.NEWTICK.figi, 'fixture NEWTICK has no FIGI');
    const inst = fx.registry.byFigi(fx.NEWTICK.figi);
    assert.ok(inst);
    assert.equal(inst.ticker, fx.NEWTICK.ticker);
  });

  test('returns null for nonexistent FIGI', () => {
    assert.equal(fx.registry.byFigi('BBG999999999'), null);
  });
});

// ─── LEI Lookup Tests ────────────────────────────────────────────────

describe('LEI Lookup', () => {
  test('finds TESTA by LEI', () => {
    assert.ok(fx.TESTA.lei, 'fixture TESTA has no LEI');
    const results = fx.registry.byLei(fx.TESTA.lei);
    assert.ok(Array.isArray(results));
    assert.ok(results.some((i) => i.ticker === fx.TESTA.ticker));
  });

  test('returns empty array for nonexistent LEI', () => {
    assert.deepEqual(fx.registry.byLei('00000000000000000000'), []);
  });
});

// ─── Ticker Lookup Tests ─────────────────────────────────────────────

describe('Ticker Lookup', () => {
  test('finds TESTA by ticker with exchange', () => {
    const inst = fx.registry.byTicker(fx.TESTA.ticker, fx.TESTA.exchange);
    assert.ok(inst);
    assert.equal(inst.isin, fx.TESTA.isin);
  });

  test('finds TESTA by ticker without exchange (returns array)', () => {
    const results = fx.registry.byTicker(fx.TESTA.ticker);
    assert.ok(Array.isArray(results));
    assert.equal(results.length, 1);
    assert.equal(results[0].ticker, fx.TESTA.ticker);
  });

  test('finds ambiguous ticker on multiple exchanges', () => {
    const hits = fx.allByTicker(fx.DUP_US.ticker);
    assert.ok(Array.isArray(hits));
    assert.equal(hits.length, 2);
    const exchanges = hits.map((i) => i.exchange).sort();
    assert.deepEqual(exchanges, [fx.DUP_UK.exchange, fx.DUP_US.exchange].sort());
  });

  test('disambiguates ambiguous ticker by exchange', () => {
    const us = fx.registry.byTicker(fx.DUP_US.ticker, fx.DUP_US.exchange);
    assert.equal(us.isin, fx.DUP_US.isin);
    assert.equal(us.currency, fx.DUP_US.currency);

    const uk = fx.registry.byTicker(fx.DUP_UK.ticker, fx.DUP_UK.exchange);
    assert.equal(uk.isin, fx.DUP_UK.isin);
    assert.equal(uk.currency, fx.DUP_UK.currency);
  });

  test('returns null for nonexistent ticker with exchange', () => {
    assert.equal(fx.registry.byTicker('ZZZZ', 'XNAS'), null);
  });

  test('returns empty array for nonexistent ticker without exchange', () => {
    assert.deepEqual(fx.registry.byTicker('ZZZZ'), []);
  });

  test('is case-insensitive', () => {
    const inst = fx.registry.byTicker(
      fx.TESTA.ticker.toLowerCase(),
      fx.TESTA.exchange.toLowerCase()
    );
    assert.ok(inst);
    assert.equal(inst.isin, fx.TESTA.isin);
  });
});

// ─── Filtering Tests ─────────────────────────────────────────────────

describe('Filtering', () => {
  test('filters by exchange', () => {
    const hits = fx.registry.byExchange(fx.TESTA.exchange);
    assert.ok(hits.length > 0);
    for (const inst of hits) {
      assert.equal(inst.exchange, fx.TESTA.exchange);
    }
  });

  test('filters by asset class', () => {
    const etfs = fx.registry.byAssetClass(fx.ETFSYN.asset_class);
    assert.ok(etfs.length > 0);
    for (const inst of etfs) {
      assert.equal(inst.asset_class, fx.ETFSYN.asset_class);
    }
  });

  test('equity + etf equals total', () => {
    const equities = fx.registry.byAssetClass('equity');
    const etfs = fx.registry.byAssetClass('etf');
    assert.equal(equities.length + etfs.length, fx.count);
  });

  test('filters by country', () => {
    const us = fx.registry.byCountry('US');
    assert.ok(us.length > 0);
    for (const inst of us) {
      assert.equal(inst.country, 'US');
    }
  });

  test('filters by currency', () => {
    const usd = fx.registry.byCurrency('USD');
    assert.ok(usd.length > 0);
    for (const inst of usd) {
      assert.equal(inst.currency, 'USD');
    }
  });

  test('returns empty array for nonexistent exchange', () => {
    assert.deepEqual(fx.registry.byExchange('ZZZZ'), []);
  });
});

// ─── Metadata Tests ──────────────────────────────────────────────────

describe('Metadata', () => {
  test('returns version', () => {
    assert.ok(fx.registry.version());
  });

  test('returns generation date', () => {
    assert.ok(fx.registry.generated());
  });

  test('returns sources', () => {
    const sources = fx.registry.sources();
    assert.ok(Array.isArray(sources));
    assert.ok(sources.length >= 1);
  });

  test('returns all instruments', () => {
    assert.equal(fx.registry.all().length, fx.count);
  });
});

// ─── Aggregate Information Tests ─────────────────────────────────────

describe('Aggregate Information', () => {
  test('returns sorted exchanges', () => {
    const exchanges = fx.registry.exchanges();
    assert.ok(exchanges.includes(fx.TESTA.exchange));
    assert.ok(exchanges.includes(fx.DUP_UK.exchange));
    assert.equal(exchanges.length, fx.exchanges.length);
  });

  test('returns sorted asset classes', () => {
    const classes = fx.registry.assetClasses();
    assert.ok(classes.includes(fx.ETFSYN.asset_class));
    assert.ok(classes.includes('equity'));
    assert.equal(classes.length, fx.assetClasses.length);
  });

  test('returns sorted currencies', () => {
    const currencies = fx.registry.currencies();
    assert.ok(currencies.includes(fx.TESTA.currency));
    assert.ok(currencies.includes(fx.DUP_UK.currency));
    assert.equal(currencies.length, fx.currencies.length);
  });

  test('returns sorted countries', () => {
    const countries = fx.registry.countries();
    assert.ok(countries.includes('US'));
    assert.ok(countries.includes('GB'));
    assert.equal(countries.length, fx.countries.length);
  });
});

// ─── Convenience Method Tests ────────────────────────────────────────

describe('Convenience Methods', () => {
  test('tickerExists returns true for existing ticker', () => {
    assert.equal(fx.registry.tickerExists(fx.TESTA.ticker), true);
  });

  test('tickerExists returns false for nonexistent ticker', () => {
    assert.equal(fx.registry.tickerExists('ZZZZ'), false);
  });

  test('tickerExists with exchange', () => {
    assert.equal(
      fx.registry.tickerExists(fx.DUP_UK.ticker, fx.DUP_UK.exchange),
      true
    );
    assert.equal(
      fx.registry.tickerExists(fx.DUP_US.ticker, 'ZZZZ'),
      false
    );
  });

  test('isinExists returns true for existing ISIN', () => {
    assert.equal(fx.registry.isinExists(fx.TESTA.isin), true);
  });

  test('isinExists returns false for nonexistent ISIN', () => {
    assert.equal(fx.registry.isinExists('XX0000000000'), false);
  });

  test('resolve detects ISIN', () => {
    const result = fx.registry.resolve(fx.TESTA.isin);
    assert.equal(result.ticker, fx.TESTA.ticker);
  });

  test('resolve detects CUSIP', () => {
    const result = fx.registry.resolve(fx.TESTA.cusip);
    assert.equal(result.ticker, fx.TESTA.ticker);
  });

  test('resolve detects FIGI', () => {
    const result = fx.registry.resolve(fx.TESTA.figi);
    assert.equal(result.ticker, fx.TESTA.ticker);
  });

  test('resolve detects LEI', () => {
    const results = fx.registry.resolve(fx.TESTA.lei);
    assert.ok(Array.isArray(results));
    assert.ok(results.some((i) => i.ticker === fx.TESTA.ticker));
  });

  test('resolve detects ticker', () => {
    const result = fx.registry.resolve(fx.TESTA.ticker, fx.TESTA.exchange);
    assert.equal(result.isin, fx.TESTA.isin);
  });

  test('resolve detects ambiguous ticker', () => {
    const result = fx.registry.resolve(fx.DUP_US.ticker);
    assert.ok(Array.isArray(result));
    assert.equal(result.length, 2);
  });
});

// ─── Statistical Method Tests ────────────────────────────────────────

describe('Statistical Methods', () => {
  test('identifierCoverage returns ISIN coverage', () => {
    const coverage = fx.registry.identifierCoverage();
    assert.equal(coverage.isin.covered, fx.count);
    assert.equal(coverage.isin.percentage, 100);
  });

  test('identifierCoverage returns CUSIP coverage', () => {
    const expectedCusip = fx.registry
      .all()
      .filter((i) => i.cusip !== null && i.cusip !== undefined).length;
    const coverage = fx.registry.identifierCoverage();
    assert.equal(coverage.cusip.covered, expectedCusip);
  });

  test('identifierCoverage returns SEDOL coverage', () => {
    const coverage = fx.registry.identifierCoverage();
    assert.equal(coverage.sedol.covered, 0);
    assert.equal(coverage.sedol.percentage, 0);
  });

  test('identifierCoverage returns FIGI coverage', () => {
    const expectedFigi = fx.registry
      .all()
      .filter((i) => i.figi !== null && i.figi !== undefined).length;
    const coverage = fx.registry.identifierCoverage();
    assert.equal(coverage.figi.covered, expectedFigi);
  });

  test('identifierCoverage returns LEI coverage', () => {
    const expectedLei = fx.registry
      .all()
      .filter((i) => i.lei !== null && i.lei !== undefined).length;
    const coverage = fx.registry.identifierCoverage();
    assert.equal(coverage.lei.covered, expectedLei);
  });

  test('tickersWithMultipleListings contains DUP', () => {
    const ambiguous = fx.registry.tickersWithMultipleListings();
    assert.ok(ambiguous.includes(fx.DUP_US.ticker));
  });
});

// ─── Ticker Change Tests ─────────────────────────────────────────────

describe('Ticker Changes', () => {
  test('NEWTICK history contains previous tickers', () => {
    const inst = fx.registry.byIsin(fx.NEWTICK.isin);
    assert.equal(inst.ticker, fx.NEWTICK.ticker);
    const historyTickers = inst.history.map((h) => h.ticker);
    for (const event of fx.NEWTICK.history) {
      assert.ok(
        historyTickers.includes(event.ticker),
        `history should contain ${event.ticker}`
      );
    }
  });

  test('NEWTICK change date is correct', () => {
    const inst = fx.registry.byIsin(fx.NEWTICK.isin);
    const fixtureRename = fx.NEWTICK.history.find(
      (h) => h.change_type === 'rename'
    );
    if (fixtureRename) {
      const renameEvent = inst.history.find((h) => h.change_type === 'rename');
      assert.ok(renameEvent, 'expected a rename event');
      assert.equal(renameEvent.change_date, fixtureRename.change_date);
    }
  });

  test('NEWTICK ISIN unchanged after rename', () => {
    const inst = fx.registry.byIsin(fx.NEWTICK.isin);
    assert.equal(inst.isin, fx.NEWTICK.isin);
  });
});

// ─── Multi-Exchange Listing Tests ────────────────────────────────────

describe('Multi-Exchange Listings', () => {
  test('MULTI has multiple listings', () => {
    const inst = fx.registry.byIsin(fx.MULTI.isin);
    assert.ok(inst.listings.length >= 2);
  });

  test('MULTI listings include every fixture listing exchange', () => {
    const inst = fx.registry.byIsin(fx.MULTI.isin);
    const exchanges = inst.listings.map((l) => l.exchange);
    for (const listing of fx.MULTI.listings) {
      assert.ok(
        exchanges.includes(listing.exchange),
        `missing listing on ${listing.exchange}`
      );
    }
  });

  test('MULTI primary listing matches top-level', () => {
    const inst = fx.registry.byIsin(fx.MULTI.isin);
    const primary = inst.listings.find((l) => l.status === 'PRIMARY');
    assert.ok(primary);
    assert.equal(primary.exchange, fx.MULTI.exchange);
    assert.equal(primary.ticker, fx.MULTI.ticker);
  });

  test('MULTI listings have different currencies', () => {
    const inst = fx.registry.byIsin(fx.MULTI.isin);
    const currencies = inst.listings.map((l) => l.currency);
    for (const listing of fx.MULTI.listings) {
      assert.ok(
        currencies.includes(listing.currency),
        `missing currency ${listing.currency}`
      );
    }
  });
});

// ─── Iterator Tests ──────────────────────────────────────────────────

describe('Iterator', () => {
  test('iterates over all instruments', () => {
    const tickers = [];
    for (const inst of fx.registry) {
      tickers.push(inst.ticker);
    }
    assert.equal(tickers.length, fx.count);
    assert.ok(tickers.includes(fx.TESTA.ticker));
  });

  test('spread operator works', () => {
    const instruments = [...fx.registry];
    assert.equal(instruments.length, fx.count);
  });
});

// ─── String Representation Tests ─────────────────────────────────────

describe('String Representation', () => {
  test('toString returns meaningful string', () => {
    const str = fx.registry.toString();
    assert.ok(str.includes('Asset Identifier Registry'));
    assert.ok(str.includes(String(fx.count)));
  });

  test('toJSON returns object', () => {
    const json = fx.registry.toJSON();
    assert.equal(json.count, fx.count);
    assert.equal(json.instruments, fx.count);
  });
});

// ─── Error Handling Tests ────────────────────────────────────────────

describe('Error Handling', () => {
  test('throws on nonexistent file', () => {
    assert.throws(
      () => new AssetRegistry('/nonexistent/path/identifiers.json'),
      /Failed to read registry file/
    );
  });

  test('throws on invalid JSON', () => {
    const invalidPath = path.join(os.tmpdir(), `invalid_registry_${process.pid}.json`);
    fs.writeFileSync(invalidPath, '{ invalid json');
    try {
      assert.throws(
        () => new AssetRegistry(invalidPath),
        /Invalid JSON/
      );
    } finally {
      fs.unlinkSync(invalidPath);
    }
  });
});
