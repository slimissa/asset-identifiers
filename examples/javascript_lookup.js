#!/usr/bin/env node
/**
 * Asset Identifier Registry — JavaScript usage example.
 *
 * This example demonstrates all major features of the
 * JavaScript wrapper for the asset identifier registry.
 *
 * Run:
 *   cd examples
 *   node javascript_lookup.js
 */

'use strict';

const path = require('path');
const { AssetRegistry } = require('../wrappers/javascript/src/index.js');

// ─── Helpers ──────────────────────────────────────────────────────────

function printSection(title) {
  console.log();
  console.log('═'.repeat(60));
  console.log(`  ${title}`);
  console.log('═'.repeat(60));
}

function derefOrNil(value) {
  return value !== null && value !== undefined ? value : 'nil';
}

// ─── Main ─────────────────────────────────────────────────────────────

function main() {
  // ─── Load the Registry ──────────────────────────────────────────

  const registryPath = path.resolve(__dirname, '..', 'identifiers.json');
  const registry = new AssetRegistry(registryPath);

  printSection('Registry Overview');
  console.log(`Version:     ${registry.version()}`);
  console.log(`Generated:   ${registry.generated()}`);
  console.log(`Instruments: ${registry.count}`);
  console.log(`Path:        ${registry.path}`);
  console.log(`Sources:     ${registry.sources().join(', ')}`);

  // ─── Lookup by ISIN ─────────────────────────────────────────────

  printSection('Lookup by ISIN');

  const aapl = registry.byIsin('US0378331005');
  if (!aapl) {
    console.error('ERROR: AAPL not found');
    process.exit(1);
  }

  console.log(`Ticker:      ${aapl.ticker}`);
  console.log(`Name:        ${aapl.name}`);
  console.log(`Exchange:    ${aapl.exchange}`);
  console.log(`Currency:    ${aapl.currency}`);
  console.log(`Asset class: ${aapl.asset_class}`);
  console.log(`CUSIP:       ${derefOrNil(aapl.cusip)}`);
  console.log(`FIGI:        ${derefOrNil(aapl.figi)}`);
  console.log(`LEI:         ${derefOrNil(aapl.lei)}`);
  console.log(`Active:      ${aapl.active}`);
  console.log(`Country:     ${derefOrNil(aapl.country)}`);

  // ─── Lookup by Other Identifiers ────────────────────────────────

  printSection('Lookup by Other Identifiers');

  const msft = registry.byCusip('594918104');
  if (msft) {
    console.log(`By CUSIP 594918104 → ${msft.ticker} (${msft.name})`);
  }

  const aaplFigi = registry.byFigi('BBG000B9XRY4');
  if (aaplFigi) {
    console.log(`By FIGI BBG000B9XRY4 → ${aaplFigi.ticker} (${aaplFigi.name})`);
  }

  const aaplLei = registry.byLei('HWUPKR0MPOU8FGXBT394');
  if (aaplLei) {
    console.log(`By LEI HWUPKR... → ${aaplLei.ticker} (${aaplLei.name})`);
  }

  // ─── Ticker Lookup ──────────────────────────────────────────────

  printSection('Ticker Lookup');

  const aaplTicker = registry.byTicker('AAPL', 'XNAS');
  if (aaplTicker) {
    console.log(`AAPL on XNAS → ${aaplTicker.isin}`);
  }

  const pruAll = registry.byTicker('PRU');
  console.log(`PRU (all exchanges): ${pruAll.length} results`);
  for (const pru of pruAll) {
    console.log(`  ${pru.ticker} on ${pru.exchange} → ${pru.isin} (${pru.name})`);
  }

  const pruLondon = registry.byTicker('PRU', 'XLON');
  if (pruLondon) {
    console.log(`PRU on XLON → ${pruLondon.isin} (${pruLondon.name}, ${pruLondon.currency})`);
  }

  const pruNyse = registry.byTicker('PRU', 'XNYS');
  if (pruNyse) {
    console.log(`PRU on XNYS → ${pruNyse.isin} (${pruNyse.name}, ${pruNyse.currency})`);
  }

  // ─── Filtering ──────────────────────────────────────────────────

  printSection('Filtering');

  const nasdaq = registry.byExchange('XNAS');
  console.log(`NASDAQ (XNAS): ${nasdaq.length} instruments`);

  const etfs = registry.byAssetClass('etf');
  console.log(`ETFs: ${etfs.length} instruments`);
  for (const etf of etfs) {
    console.log(`  ${etf.ticker} (${etf.name})`);
  }

  const usInstruments = registry.byCountry('US');
  console.log(`US instruments: ${usInstruments.length}`);

  const usdInstruments = registry.byCurrency('USD');
  console.log(`USD instruments: ${usdInstruments.length}`);

  // ─── Aggregate Information ──────────────────────────────────────

  printSection('Aggregate Information');

  console.log(`Exchanges:    [${registry.exchanges().join(' ')}]`);
  console.log(`Asset classes: [${registry.assetClasses().join(' ')}]`);
  console.log(`Currencies:   [${registry.currencies().join(' ')}]`);
  console.log(`Countries:    [${registry.countries().join(' ')}]`);

  // ─── Identifier Coverage ────────────────────────────────────────

  printSection('Identifier Coverage');

  const coverage = registry.identifierCoverage();

  console.log(`ISIN:  ${coverage.isin.covered}/${coverage.isin.total} (${coverage.isin.percentage.toFixed(1)}%)`);
  console.log(`CUSIP: ${coverage.cusip.covered}/${coverage.cusip.total} (${coverage.cusip.percentage.toFixed(1)}%)`);
  console.log(`SEDOL: ${coverage.sedol.covered}/${coverage.sedol.total} (${coverage.sedol.percentage.toFixed(1)}%)`);
  console.log(`FIGI:  ${coverage.figi.covered}/${coverage.figi.total} (${coverage.figi.percentage.toFixed(1)}%)`);
  console.log(`LEI:   ${coverage.lei.covered}/${coverage.lei.total} (${coverage.lei.percentage.toFixed(1)}%)`);

  // ─── Ticker Changes ─────────────────────────────────────────────

  printSection('Ticker Changes');

  const meta = registry.byIsin('US30303M1027');
  if (meta) {
    console.log(`Current ticker: ${meta.ticker}`);
    console.log(`ISIN:           ${meta.isin} (unchanged)`);
    console.log('History:');
    for (const event of meta.history) {
      console.log(`  ${event.ticker}  ${event.change_date}  ${event.change_type}  (${derefOrNil(event.reason)})`);
    }
  }

  // ─── Multi-Exchange Listings ────────────────────────────────────

  printSection('Multi-Exchange Listings');

  for (const listing of aapl.listings) {
    console.log(`${listing.exchange}: ${listing.ticker} (${listing.currency}, ${listing.status})`);
  }

  // ─── Ambiguous Tickers ──────────────────────────────────────────

  printSection('Ambiguous Tickers');

  const ambiguous = registry.tickersWithMultipleListings();
  console.log(`Tickers with multiple listings: [${ambiguous.join(', ')}]`);

  // ─── Existence Checks ───────────────────────────────────────────

  printSection('Existence Checks');

  console.log(`US0378331005 exists: ${registry.isinExists('US0378331005')}`);
  console.log(`XX0000000000 exists: ${registry.isinExists('XX0000000000')}`);
  console.log(`AAPL on XNAS exists: ${registry.tickerExists('AAPL', 'XNAS')}`);
  console.log(`PRU anywhere exists: ${registry.tickerExists('PRU')}`);
  console.log(`ZZZZ exists:         ${registry.tickerExists('ZZZZ')}`);

  // ─── Resolve (auto-detect) ──────────────────────────────────────

  printSection('Resolve (auto-detect identifier type)');

  console.log(`resolve('US0378331005') → ${registry.resolve('US0378331005').ticker}`);
  console.log(`resolve('037833100')    → ${registry.resolve('037833100').ticker}`);
  console.log(`resolve('BBG000B9XRY4') → ${registry.resolve('BBG000B9XRY4').ticker}`);
  console.log(`resolve('AAPL', 'XNAS') → ${registry.resolve('AAPL', 'XNAS').isin}`);

  // ─── Iteration ──────────────────────────────────────────────────

  printSection('Iteration (first 10)');

  let count = 0;
  for (const inst of registry) {
    if (count >= 10) {
      console.log('  ...');
      break;
    }
    console.log(`  ${inst.ticker} (${inst.exchange}): ${inst.isin}`);
    count++;
  }

  // ─── String Representation ──────────────────────────────────────

  printSection('String Representation');

  console.log(registry.toString());

  console.log();
  console.log('Example complete.');
}

// ─── Run ─────────────────────────────────────────────────────────────

main();