#!/usr/bin/env node
/**
 * Fixture-derived test anchors.
 *
 * Single source of truth for every JavaScript test assertion. Tests must
 * not hardcode fixture values; they import constants from this module.
 *
 * If a fixture value changes and an anchor disappears, this module throws
 * at require() time. Do not hardcode. Import from here.
 */

'use strict';

const path = require('path');
const { AssetRegistry } = require('../src/index.js');

const FIXTURE_PATH = path.resolve(
  __dirname,
  '../../../tests/fixtures/identifiers.test.json'
);

const registry = new AssetRegistry(FIXTURE_PATH);

// ─── Lookup helpers ──────────────────────────────────────────────────

function byTickerExchange(ticker, exchange) {
  const hit = registry.byTicker(ticker, exchange);
  if (!hit) {
    throw new Error(`fixture missing: ${ticker}@${exchange}`);
  }
  return hit;
}

function allByTicker(ticker) {
  const hits = registry.byTicker(ticker);
  if (!Array.isArray(hits)) {
    return [];
  }
  return hits;
}

// ─── Anchors ─────────────────────────────────────────────────────────

const TESTA   = byTickerExchange('TESTA',   'XNAS');
const TESTB   = byTickerExchange('TESTB',   'XNAS');
const NEWTICK = byTickerExchange('NEWTICK', 'XNAS');
const MULTI   = byTickerExchange('MULTI',   'XNAS');
const DUP_US  = byTickerExchange('DUP',     'XNAS');
const DUP_UK  = byTickerExchange('DUP',     'XLON');
const ETFSYN  = byTickerExchange('ETFSYN',  'XNAS');

module.exports = {
  registry,
  FIXTURE_PATH,

  byTickerExchange,
  allByTicker,

  TESTA,
  TESTB,
  NEWTICK,
  MULTI,
  DUP_US,
  DUP_UK,
  ETFSYN,

  count:      registry.count,
  meta:       registry.meta(),

  // Convenience sets derived from the fixture itself
  ambiguousTickers: registry.tickersWithMultipleListings(),
  exchanges:        registry.exchanges(),
  assetClasses:     registry.assetClasses(),
  currencies:       registry.currencies(),
  countries:        registry.countries(),
};