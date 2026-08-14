/**
 * Asset Identifier Registry — TypeScript declarations.
 *
 * Type definitions for the JavaScript wrapper.
 * Provides full type safety for all registry operations.
 */

declare module 'asset-identifiers-registry' {
  /**
   * Asset class enumeration.
   */
  export type AssetClass = 'equity' | 'etf' | 'bond' | 'option' | 'future' | 'other';

  /**
   * Instrument type enumeration.
   */
  export type InstrumentType =
    | 'COMMON_STOCK'
    | 'PREFERRED_STOCK'
    | 'ETF'
    | 'CORPORATE_BOND'
    | 'GOVERNMENT_BOND'
    | 'OPTION'
    | 'FUTURE'
    | string;

  /**
   * Listing status enumeration.
   */
  export type ListingStatus =
    | 'PRIMARY'
    | 'SECONDARY'
    | 'DEPOSITARY_RECEIPT'
    | 'DELISTED';

  /**
   * Corporate action type enumeration.
   */
  export type CorporateActionType =
    | 'SPLIT'
    | 'REVERSE_SPLIT'
    | 'DIVIDEND'
    | 'SPINOFF'
    | 'MERGER'
    | 'ACQUISITION'
    | 'RIGHTS_ISSUE'
    | 'BUYBACK';

  /**
   * Ticker change type enumeration.
   */
  export type ChangeType =
    | 'none'
    | 'rename'
    | 'delisting'
    | 'relisting'
    | 'merger'
    | 'acquisition'
    | 'spinoff'
    | 'split'
    | 'reverse_split';

  /**
   * Exchange listing information.
   */
  export interface ExchangeListing {
    /** Exchange MIC code (ISO 10383) */
    exchange: string;
    /** Ticker symbol on this exchange */
    ticker: string;
    /** Trading currency (ISO 4217) */
    currency: string;
    /** Listing status */
    status: ListingStatus;
    /** Date listed */
    listing_date: string | null;
    /** Date delisted, if applicable */
    delisting_date: string | null;
  }

  /**
   * Ticker change history event.
   */
  export interface HistoryEvent {
    /** Ticker after this event */
    ticker: string;
    /** Date the change took effect */
    change_date: string;
    /** Type of change */
    change_type: ChangeType;
    /** Reason for the change */
    reason: string | null;
    /** Source of the announcement */
    source: string | null;
    /** URL to the announcement */
    source_url: string | null;
  }

  /**
   * Corporate action event.
   */
  export interface CorporateAction {
    /** Date the action occurred */
    date: string;
    /** Type of action */
    action_type: CorporateActionType;
    /** Ratio for splits (e.g., "4:1") */
    ratio: string | null;
    /** Additional details */
    details: string | null;
    /** Source */
    source: string | null;
    /** URL to the announcement */
    source_url: string | null;
  }

  /**
   * Financial instrument.
   */
  export interface Instrument {
    /** ISO 6166 ISIN (12 characters) */
    isin: string;
    /** CUSIP (9 characters, US/Canada) */
    cusip: string | null;
    /** SEDOL (7 characters, UK/Europe) */
    sedol: string | null;
    /** Financial Instrument Global Identifier (12 characters) */
    figi: string | null;
    /** Legal Entity Identifier (20 characters) */
    lei: string | null;
    /** Current ticker on primary exchange */
    ticker: string;
    /** Primary exchange MIC code */
    exchange: string;
    /** Legal entity name */
    name: string;
    /** Primary trading currency (ISO 4217) */
    currency: string;
    /** Asset class */
    asset_class: AssetClass;
    /** Specific instrument type */
    instrument_type: InstrumentType | null;
    /** Business sector */
    sector: string | null;
    /** Industry */
    industry: string | null;
    /** Country of domicile (ISO 3166-1 alpha-2) */
    country: string | null;
    /** Whether currently listed */
    active: boolean;
    /** Initial listing date */
    listing_date: string | null;
    /** Delisting date, if applicable */
    delisting_date: string | null;
    /** All exchange listings */
    listings: ExchangeListing[];
    /** Ticker change history */
    history: HistoryEvent[];
    /** Corporate actions */
    corporate_actions: CorporateAction[];
  }

  /**
   * Registry coverage information.
   */
  export interface RegistryCoverage {
    /** List of exchanges (MIC codes) */
    exchanges: string[];
    /** List of asset classes */
    asset_classes: AssetClass[];
    /** List of countries (ISO 3166-1 alpha-2) */
    countries: string[];
  }

  /**
   * Registry metadata.
   */
  export interface RegistryMeta {
    /** Registry version (semver) */
    version: string;
    /** Generation date */
    generated: string;
    /** Instrument count */
    count: number;
    /** Data sources */
    sources: string[];
    /** Coverage statistics */
    coverage: RegistryCoverage;
    /** Build timestamp */
    build_timestamp?: string;
  }

  /**
   * Identifier coverage statistics for a single identifier type.
   */
  export interface IdentifierCoverageStat {
    /** Number of instruments with this identifier */
    covered: number;
    /** Total instruments */
    total: number;
    /** Coverage percentage (0-100) */
    percentage: number;
  }

  /**
   * Identifier coverage for all identifier types.
   */
  export interface IdentifierCoverage {
    isin: IdentifierCoverageStat;
    cusip: IdentifierCoverageStat;
    sedol: IdentifierCoverageStat;
    figi: IdentifierCoverageStat;
    lei: IdentifierCoverageStat;
  }

  /**
   * Asset Identifier Registry wrapper class.
   *
   * Loads a JSON registry of financial instruments and provides
   * indexed lookup methods for various identifier types.
   *
   * @example
   * ```typescript
   * import { AssetRegistry } from 'asset-identifiers-registry';
   *
   * const registry = new AssetRegistry('identifiers.json');
   * const aapl = registry.byIsin('US0378331005');
   * console.log(aapl?.ticker); // AAPL
   * ```
   */
  export class AssetRegistry {
    /**
     * Create a new AssetRegistry instance.
     *
     * @param path - Path to identifiers.json (default: "identifiers.json")
     * @throws {Error} If the file does not exist or is invalid JSON
     */
    constructor(path?: string);

    /**
     * Number of instruments in the registry.
     */
    readonly count: number;

    /**
     * List of all instrument objects.
     */
    readonly instruments: Instrument[];

    /**
     * Path to the registry file.
     */
    readonly path: string;

    /**
     * Return registry metadata.
     */
    meta(): RegistryMeta;

    /**
     * Return registry version.
     */
    version(): string;

    /**
     * Return registry generation date.
     */
    generated(): string;

    /**
     * Return list of data sources.
     */
    sources(): string[];

    /**
     * Return all instruments.
     */
    all(): Instrument[];

    /**
     * Look up an instrument by ISIN.
     *
     * @param isin - 12-character ISIN (e.g., "US0378331005")
     * @returns Instrument or null if not found
     */
    byIsin(isin: string): Instrument | null;

    /**
     * Look up an instrument by CUSIP.
     *
     * @param cusip - 9-character CUSIP (e.g., "037833100")
     * @returns Instrument or null if not found
     */
    byCusip(cusip: string): Instrument | null;

    /**
     * Look up an instrument by SEDOL.
     *
     * @param sedol - 7-character SEDOL (e.g., "2046251")
     * @returns Instrument or null if not found
     */
    bySedol(sedol: string): Instrument | null;

    /**
     * Look up an instrument by FIGI.
     *
     * @param figi - 12-character FIGI (e.g., "BBG000B9XRY4")
     * @returns Instrument or null if not found
     */
    byFigi(figi: string): Instrument | null;

    /**
     * Look up an instrument by LEI.
     *
     * @param lei - 20-character LEI
     * @returns Instrument or null if not found
     */
    byLei(lei: string): Instrument | null;

    /**
     * Look up instruments by ticker symbol.
     *
     * @param ticker - Ticker symbol (e.g., "AAPL", "PRU")
     * @param exchange - Optional MIC code to disambiguate
     * @returns Instrument, array of instruments, or null
     */
    byTicker(ticker: string, exchange?: string): Instrument | Instrument[] | null;

    /**
     * Return all instruments on a given exchange.
     *
     * @param exchange - MIC code (e.g., "XNAS")
     */
    byExchange(exchange: string): Instrument[];

    /**
     * Return all instruments of a given asset class.
     *
     * @param assetClass - Asset class (e.g., "equity", "etf")
     */
    byAssetClass(assetClass: AssetClass | string): Instrument[];

    /**
     * Return all instruments from a given country.
     *
     * @param country - ISO 3166-1 alpha-2 code (e.g., "US")
     */
    byCountry(country: string): Instrument[];

    /**
     * Return all instruments trading in a given currency.
     *
     * @param currency - ISO 4217 code (e.g., "USD")
     */
    byCurrency(currency: string): Instrument[];

    /**
     * Return sorted list of all exchanges.
     */
    exchanges(): string[];

    /**
     * Return sorted list of all asset classes.
     */
    assetClasses(): AssetClass[];

    /**
     * Return sorted list of all currencies.
     */
    currencies(): string[];

    /**
     * Return sorted list of all countries.
     */
    countries(): string[];

    /**
     * Check if a ticker exists.
     *
     * @param ticker - Ticker symbol
     * @param exchange - Optional MIC code
     */
    tickerExists(ticker: string, exchange?: string): boolean;

    /**
     * Check if an ISIN exists.
     *
     * @param isin - ISIN code
     */
    isinExists(isin: string): boolean;

    /**
     * Resolve any identifier type to an instrument.
     *
     * Auto-detects identifier type by length and format:
     * - 12 chars starting with BBG → FIGI
     * - 12 chars → ISIN
     * - 9 chars → CUSIP
     * - 7 chars → SEDOL
     * - 20 chars → LEI
     * - Otherwise → ticker
     *
     * @param identifier - Any identifier string
     * @param exchange - Optional MIC code for ticker disambiguation
     */
    resolve(identifier: string, exchange?: string): Instrument | Instrument[] | null;

    /**
     * Return identifier coverage statistics.
     */
    identifierCoverage(): IdentifierCoverage;

    /**
     * Return tickers that appear on multiple exchanges.
     */
    tickersWithMultipleListings(): string[];

    /**
     * Iterate over all instruments.
     */
    [Symbol.iterator](): Iterator<Instrument>;

    /**
     * String representation.
     */
    toString(): string;

    /**
     * JSON representation.
     */
    toJSON(): object;
  }

  /**
   * Default export.
   */
  export default AssetRegistry;
}