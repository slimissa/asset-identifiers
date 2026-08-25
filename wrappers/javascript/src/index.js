#!/usr/bin/env node
/**
 * Asset Identifier Registry — JavaScript wrapper.
 *
 * A lightweight, dependency-free JavaScript interface to the
 * canonical asset identifier registry (identifiers.json).
 *
 * Example:
 *   const { AssetRegistry } = require('asset-identifiers-registry');
 *
 *   const registry = new AssetRegistry('identifiers.json');
 *
 *   // Look up by ISIN
 *   const aapl = registry.byIsin('US0378331005');
 *   console.log(aapl.ticker);  // AAPL
 *
 *   // Look up by ticker on a specific exchange
 *   const pru = registry.byTicker('PRU', 'XNYS');
 *   console.log(pru.isin);  // US7443201022
 *
 *   // Look up by ticker without exchange (returns array)
 *   const pruAll = registry.byTicker('PRU');
 *   console.log(pruAll.length);  // 2
 *
 *   // Iterate over all instruments
 *   for (const instrument of registry) {
 *     console.log(instrument.ticker);
 *   }
 */

'use strict';

const fs = require('fs');
const path = require('path');

class AssetRegistry {
  /**
   * Asset Identifier Registry wrapper.
   *
   * Loads a JSON registry of financial instruments and provides
   * lookup methods for various identifier types.
   *
   * @param {string} filePath - Path to identifiers.json
   * @throws {Error} If the file does not exist or is invalid JSON
   */
  constructor(filePath = 'identifiers.json') {
    this._path = path.resolve(filePath);
    this._load();
    this._buildIndices();
  }

  /**
   * Load the registry from disk.
   * @private
   */
  _load() {
    let raw;
    try {
      raw = fs.readFileSync(this._path, 'utf8');
    } catch (err) {
      throw new Error(`Failed to read registry file: ${this._path} — ${err.message}`);
    }

    try {
      this._data = JSON.parse(raw);
    } catch (err) {
      throw new Error(`Invalid JSON in registry file: ${this._path} — ${err.message}`);
    }

    this._instruments = this._data.instruments || [];
    this._meta = this._data.meta || {};
  }

  /**
   * Build lookup indices for O(1) access.
   * @private
   */
  _buildIndices() {
    this._isinIndex = new Map();
    this._cusipIndex = new Map();
    this._sedolIndex = new Map();
    this._figiIndex = new Map();
    this._leiIndex = new Map();
    this._tickerIndex = new Map();
    this._exchangeIndex = new Map();
    this._assetClassIndex = new Map();
    this._countryIndex = new Map();
    this._currencyIndex = new Map();

    for (const inst of this._instruments) {
      const isin = inst.isin;
      if (isin) this._isinIndex.set(isin, inst);

      const cusip = inst.cusip;
      if (cusip) this._cusipIndex.set(cusip, inst);

      const sedol = inst.sedol;
      if (sedol) this._sedolIndex.set(sedol, inst);

      const figi = inst.figi;
      if (figi) this._figiIndex.set(figi, inst);

      const lei = inst.lei;
      if (lei) this._leiIndex.set(lei, inst);

      const ticker = inst.ticker;
      if (ticker) {
        if (!this._tickerIndex.has(ticker)) {
          this._tickerIndex.set(ticker, []);
        }
        this._tickerIndex.get(ticker).push(inst);
      }

      const exchange = inst.exchange;
      if (exchange) {
        if (!this._exchangeIndex.has(exchange)) {
          this._exchangeIndex.set(exchange, []);
        }
        this._exchangeIndex.get(exchange).push(inst);
      }

      const assetClass = inst.asset_class;
      if (assetClass) {
        if (!this._assetClassIndex.has(assetClass)) {
          this._assetClassIndex.set(assetClass, []);
        }
        this._assetClassIndex.get(assetClass).push(inst);
      }

      const country = inst.country;
      if (country) {
        if (!this._countryIndex.has(country)) {
          this._countryIndex.set(country, []);
        }
        this._countryIndex.get(country).push(inst);
      }

      const currency = inst.currency;
      if (currency) {
        if (!this._currencyIndex.has(currency)) {
          this._currencyIndex.set(currency, []);
        }
        this._currencyIndex.get(currency).push(inst);
      }
    }
  }

  // ─── Properties ──────────────────────────────────────────────────

  /**
   * Number of instruments in the registry.
   * @returns {number}
   */
  get count() {
    return this._instruments.length;
  }

  /**
   * List of all instrument objects.
   * @returns {Object[]}
   */
  get instruments() {
    return this._instruments;
  }

  /**
   * Path to the registry file.
   * @returns {string}
   */
  get path() {
    return this._path;
  }

  // ─── Metadata ────────────────────────────────────────────────────

  /**
   * Return registry metadata.
   * @returns {Object}
   */
  meta() {
    return this._meta;
  }

  /**
   * Return registry version.
   * @returns {string}
   */
  version() {
    return this._meta.version || 'unknown';
  }

  /**
   * Return registry generation date.
   * @returns {string}
   */
  generated() {
    return this._meta.generated || 'unknown';
  }

  /**
   * Return list of data sources.
   * @returns {string[]}
   */
  sources() {
    return this._meta.sources || [];
  }

  // ─── Bulk Access ─────────────────────────────────────────────────

  /**
   * Return all instruments.
   * @returns {Object[]}
   */
  all() {
    return this._instruments;
  }

  /**
   * Iterate over all instruments.
   * @returns {Iterator<Object>}
   */
  [Symbol.iterator]() {
    return this._instruments[Symbol.iterator]();
  }

  /**
   * String representation.
   * @returns {string}
   */
  toString() {
    return `Asset Identifier Registry v${this.version()} (${this.count} instruments)`;
  }

  /**
   * JSON representation.
   * @returns {Object}
   */
  toJSON() {
    return {
      count: this.count,
      version: this.version(),
      instruments: this._instruments.length,
    };
  }

  // ─── Lookup by Identifier ────────────────────────────────────────

  /**
   * Look up an instrument by ISIN.
   * @param {string} isin - 12-character ISIN (e.g., US0378331005)
   * @returns {Object|null} Instrument object or null
   */
  byIsin(isin) {
    return this._isinIndex.get(isin.toUpperCase()) || null;
  }

  /**
   * Look up an instrument by CUSIP.
   * @param {string} cusip - 9-character CUSIP (e.g., 037833100)
   * @returns {Object|null} Instrument object or null
   */
  byCusip(cusip) {
    return this._cusipIndex.get(cusip.toUpperCase()) || null;
  }

  /**
   * Look up an instrument by SEDOL.
   * @param {string} sedol - 7-character SEDOL (e.g., 2046251)
   * @returns {Object|null} Instrument object or null
   */
  bySedol(sedol) {
    return this._sedolIndex.get(sedol.toUpperCase()) || null;
  }

  /**
   * Look up an instrument by FIGI.
   * @param {string} figi - 12-character FIGI (e.g., BBG000B9XRY4)
   * @returns {Object|null} Instrument object or null
   */
  byFigi(figi) {
    return this._figiIndex.get(figi.toUpperCase()) || null;
  }

  /**
   * Look up an instrument by LEI.
   * @param {string} lei - 20-character LEI
   * @returns {Object|null} Instrument object or null
   */
  byLei(lei) {
    return this._leiIndex.get(lei.toUpperCase()) || null;
  }

  // ─── Lookup by Ticker ────────────────────────────────────────────

  /**
   * Look up instruments by ticker symbol.
   *
   * @param {string} ticker - Ticker symbol (e.g., AAPL, PRU)
   * @param {string} [exchange] - Optional MIC code to disambiguate
   * @returns {Object|Object[]|null}
   *   If exchange provided: Instrument object or null
   *   If exchange not provided: Array of matching instruments
   *
   * Warning: Some tickers are ambiguous — the same symbol exists on
   * multiple exchanges. "PRU" is Prudential plc (XLON) and Prudential
   * Financial (XNYS). Always use the exchange parameter when the ticker
   * might be ambiguous. Check tickersWithMultipleListings() to detect
   * ambiguous tickers before calling without an exchange.
   */
  byTicker(ticker, exchange = null) {
    const matches = this._tickerIndex.get(ticker.toUpperCase()) || [];

    if (exchange !== null) {
      const exchangeUpper = exchange.toUpperCase();
      for (const inst of matches) {
        if (inst.exchange === exchangeUpper) {
          return inst;
        }
      }
      return null;
    }

    return matches;
  }

  // ─── Filtering ───────────────────────────────────────────────────

  /**
   * Return all instruments on a given exchange.
   * @param {string} exchange - MIC code (e.g., XNAS)
   * @returns {Object[]}
   */
  byExchange(exchange) {
    return this._exchangeIndex.get(exchange.toUpperCase()) || [];
  }

  /**
   * Return all instruments of a given asset class.
   * @param {string} assetClass - Asset class (equity, etf, etc.)
   * @returns {Object[]}
   */
  byAssetClass(assetClass) {
    return this._assetClassIndex.get(assetClass.toLowerCase()) || [];
  }

  /**
   * Return all instruments from a given country.
   * @param {string} country - ISO 3166-1 alpha-2 code (e.g., US)
   * @returns {Object[]}
   */
  byCountry(country) {
    return this._countryIndex.get(country.toUpperCase()) || [];
  }

  /**
   * Return all instruments trading in a given currency.
   * @param {string} currency - ISO 4217 code (e.g., USD)
   * @returns {Object[]}
   */
  byCurrency(currency) {
    return this._currencyIndex.get(currency.toUpperCase()) || [];
  }

  // ─── Aggregate Information ───────────────────────────────────────

  /**
   * Return sorted list of all exchanges.
   * @returns {string[]}
   */
  exchanges() {
    return [...this._exchangeIndex.keys()].sort();
  }

  /**
   * Return sorted list of all asset classes.
   * @returns {string[]}
   */
  assetClasses() {
    return [...this._assetClassIndex.keys()].sort();
  }

  /**
   * Return sorted list of all currencies.
   * @returns {string[]}
   */
  currencies() {
    return [...this._currencyIndex.keys()].sort();
  }

  /**
   * Return sorted list of all countries.
   * @returns {string[]}
   */
  countries() {
    return [...this._countryIndex.keys()].sort();
  }

  // ─── Convenience Methods ─────────────────────────────────────────

  /**
   * Check if a ticker exists.
   * @param {string} ticker - Ticker symbol
   * @param {string} [exchange] - Optional MIC code
   * @returns {boolean}
   */
  tickerExists(ticker, exchange = null) {
    if (exchange !== null) {
      return this.byTicker(ticker, exchange) !== null;
    }
    return this.byTicker(ticker).length > 0;
  }

  /**
   * Check if an ISIN exists.
   * @param {string} isin - ISIN code
   * @returns {boolean}
   */
  isinExists(isin) {
    return this.byIsin(isin) !== null;
  }

  /**
   * Resolve any identifier type to an instrument.
   *
   * Auto-detects identifier type:
   * - 12 chars starting with BBG → FIGI
   * - 12 chars → ISIN
   * - 9 chars → CUSIP
   * - 7 chars → SEDOL
   * - 20 chars → LEI
   * - Otherwise → ticker
   *
   * @param {string} identifier - Any identifier string
   * @param {string} [exchange] - Optional MIC code for ticker
   * @returns {Object|Object[]|null}
   */
  resolve(identifier, exchange = null) {
    const id = identifier.toUpperCase().trim();

    if (id.length === 12 && id.startsWith('BBG')) {
      return this.byFigi(id);
    } else if (id.length === 12) {
      return this.byIsin(id);
    } else if (id.length === 9) {
      return this.byCusip(id);
    } else if (id.length === 7) {
      return this.bySedol(id);
    } else if (id.length === 20) {
      return this.byLei(id);
    } else {
      return this.byTicker(id, exchange);
    }
  }

  // ─── Statistical Methods ─────────────────────────────────────────

  /**
   * Return identifier coverage statistics.
   * @returns {Object} Coverage stats for each identifier type
   */
  identifierCoverage() {
    const total = this.count;
    const stats = {};

    for (const idType of ['isin', 'cusip', 'sedol', 'figi', 'lei']) {
      const covered = this._instruments.filter((i) => i[idType]).length;
      stats[idType] = {
        covered,
        total,
        percentage: total > 0 ? Number(((100 * covered) / total).toFixed(2)) : 0,
      };
    }

    return stats;
  }

  /**
   * Return tickers that appear on multiple exchanges.
   * @returns {string[]}
   */
  tickersWithMultipleListings() {
    const result = [];
    for (const [ticker, instruments] of this._tickerIndex) {
      if (instruments.length > 1) {
        result.push(ticker);
      }
    }
    return result.sort();
  }
}

module.exports = { AssetRegistry };
module.exports.AssetRegistry = AssetRegistry;
module.exports.default = AssetRegistry;