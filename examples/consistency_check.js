#!/usr/bin/env node
/**
 * Cross-language consistency check — JavaScript side.
 *
 * Loads the synthetic test fixture, looks up every instrument by ISIN
 * through the JavaScript wrapper, and prints one tab-separated line
 * per instrument: ISIN, ticker, name.
 *
 * See consistency_check.py for the full explanation of how this fits
 * into the cross-language consistency check as a whole.
 *
 * Run:
 *   cd examples
 *   node consistency_check.js ../tests/fixtures/identifiers.test.json
 */

'use strict';

const fs = require('fs');
const { AssetRegistry } = require('../wrappers/javascript/src/index.js');

function main() {
  const fixturePath = process.argv[2];
  if (!fixturePath) {
    console.error('usage: consistency_check.js <fixture_path>');
    process.exit(2);
  }

  const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));
  const registry = new AssetRegistry(fixturePath);

  for (const expected of fixture.instruments) {
    const isin = expected.isin;
    const actual = registry.byIsin(isin);
    if (!actual) {
      console.log(`${isin}\tMISSING\tMISSING`);
    } else {
      console.log(`${isin}\t${actual.ticker}\t${actual.name}`);
    }
  }
}

main();
