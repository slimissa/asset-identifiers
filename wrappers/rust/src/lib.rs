//! Asset Identifier Registry — Rust wrapper.
//!
//! A lightweight, dependency-minimal Rust interface to the
//! canonical asset identifier registry (`identifiers.json`).
//!
//! # Example
//!
//! ```rust
//! use asset_identifiers::AssetRegistry;
//!
//! let registry = AssetRegistry::load("../../identifiers.json")?;
//!
//! // Get instrument count
//! assert_eq!(registry.count(), 50);
//!
//! // Look up by ISIN
//! let aapl = registry.by_isin("US0378331005").unwrap();
//! assert_eq!(aapl.ticker, "AAPL");
//! assert_eq!(aapl.name, "Apple Inc.");
//!
//! // Look up by ticker on a specific exchange
//! let pru_nyse = registry.by_ticker("PRU", Some("XNYS"));
//! assert_eq!(pru_nyse.len(), 1);
//! assert_eq!(pru_nyse[0].isin, "US7443201022");
//!
//! // Look up by ticker without exchange (returns Vec)
//! let pru_all = registry.by_ticker("PRU", None);
//! assert_eq!(pru_all.len(), 2);
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

// ─── Error Types ─────────────────────────────────────────────────────

/// Errors that can occur when loading or querying the registry.
#[derive(Debug, thiserror::Error)]
pub enum RegistryError {
    /// The registry file could not be read.
    #[error("Failed to read registry file: {path} — {source}")]
    FileRead {
        path: String,
        #[source]
        source: std::io::Error,
    },

    /// The registry file contains invalid JSON.
    #[error("Invalid JSON in registry file: {path} — {source}")]
    InvalidJson {
        path: String,
        #[source]
        source: serde_json::Error,
    },

    /// The registry file is missing required fields.
    #[error("Invalid registry structure: missing field '{field}'")]
    MissingField { field: &'static str },

    /// An instrument with a duplicate identifier was found.
    #[error("Duplicate {identifier_type} found: {value}")]
    DuplicateIdentifier {
        identifier_type: &'static str,
        value: String,
    },
}

/// Convenience type alias for `Result` with `RegistryError`.
pub type Result<T> = std::result::Result<T, RegistryError>;

// ─── Data Types ──────────────────────────────────────────────────────

/// Asset class enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AssetClass {
    Equity,
    Etf,
    Bond,
    Option,
    Future,
    Other,
}

/// Listing status enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ListingStatus {
    Primary,
    Secondary,
    DepositaryReceipt,
    Delisted,
}

/// Corporate action type enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
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

/// Ticker change type enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
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

/// Exchange listing information.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExchangeListing {
    /// Exchange MIC code (ISO 10383)
    pub exchange: String,
    /// Ticker symbol on this exchange
    pub ticker: String,
    /// Trading currency (ISO 4217)
    pub currency: String,
    /// Listing status
    pub status: ListingStatus,
    /// Date listed
    #[serde(default)]
    pub listing_date: Option<String>,
    /// Date delisted, if applicable
    #[serde(default)]
    pub delisting_date: Option<String>,
}

/// Ticker change history event.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HistoryEvent {
    /// Ticker after this event
    pub ticker: String,
    /// Date the change took effect
    pub change_date: String,
    /// Type of change
    pub change_type: ChangeType,
    /// Reason for the change
    #[serde(default)]
    pub reason: Option<String>,
    /// Source of the announcement
    #[serde(default)]
    pub source: Option<String>,
    /// URL to the announcement
    #[serde(default)]
    pub source_url: Option<String>,
}

/// Corporate action event.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CorporateAction {
    /// Date the action occurred
    pub date: String,
    /// Type of action
    pub action_type: CorporateActionType,
    /// Ratio for splits (e.g., "4:1")
    #[serde(default)]
    pub ratio: Option<String>,
    /// Additional details
    #[serde(default)]
    pub details: Option<String>,
    /// Source
    #[serde(default)]
    pub source: Option<String>,
    /// URL to the announcement
    #[serde(default)]
    pub source_url: Option<String>,
}

/// Financial instrument.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Instrument {
    /// ISO 6166 ISIN (12 characters)
    pub isin: String,
    /// CUSIP (9 characters, US/Canada)
    #[serde(default)]
    pub cusip: Option<String>,
    /// SEDOL (7 characters, UK/Europe)
    #[serde(default)]
    pub sedol: Option<String>,
    /// Financial Instrument Global Identifier (12 characters)
    #[serde(default)]
    pub figi: Option<String>,
    /// Legal Entity Identifier (20 characters)
    #[serde(default)]
    pub lei: Option<String>,
    /// Current ticker on primary exchange
    pub ticker: String,
    /// Primary exchange MIC code
    pub exchange: String,
    /// Legal entity name
    pub name: String,
    /// Primary trading currency (ISO 4217)
    pub currency: String,
    /// Asset class
    pub asset_class: AssetClass,
    /// Specific instrument type
    #[serde(default)]
    pub instrument_type: Option<String>,
    /// Business sector
    #[serde(default)]
    pub sector: Option<String>,
    /// Industry
    #[serde(default)]
    pub industry: Option<String>,
    /// Country of domicile (ISO 3166-1 alpha-2)
    #[serde(default)]
    pub country: Option<String>,
    /// Whether currently listed
    pub active: bool,
    /// Initial listing date
    #[serde(default)]
    pub listing_date: Option<String>,
    /// Delisting date, if applicable
    #[serde(default)]
    pub delisting_date: Option<String>,
    /// All exchange listings
    #[serde(default)]
    pub listings: Vec<ExchangeListing>,
    /// Ticker change history
    #[serde(default)]
    pub history: Vec<HistoryEvent>,
    /// Corporate actions
    #[serde(default)]
    pub corporate_actions: Vec<CorporateAction>,
}

/// Registry coverage information.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct RegistryCoverage {
    /// List of exchanges (MIC codes)
    #[serde(default)]
    pub exchanges: Vec<String>,
    /// List of asset classes
    #[serde(default)]
    pub asset_classes: Vec<String>,
    /// List of countries (ISO 3166-1 alpha-2)
    #[serde(default)]
    pub countries: Vec<String>,
}

/// Registry metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegistryMeta {
    /// Registry version (semver)
    pub version: String,
    /// Generation date
    pub generated: String,
    /// Instrument count
    pub count: usize,
    /// Data sources
    #[serde(default)]
    pub sources: Vec<String>,
    /// Coverage statistics
    #[serde(default)]
    pub coverage: RegistryCoverage,
    /// Build timestamp
    #[serde(default)]
    pub build_timestamp: Option<String>,
}

/// Top-level registry structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct RegistryData {
    meta: RegistryMeta,
    instruments: Vec<Instrument>,
}

/// Identifier coverage statistics for a single identifier type.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct IdentifierCoverageStat {
    /// Number of instruments with this identifier
    pub covered: usize,
    /// Total instruments
    pub total: usize,
    /// Coverage percentage (0-100)
    pub percentage: f64,
}

/// Identifier coverage for all identifier types.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IdentifierCoverage {
    pub isin: IdentifierCoverageStat,
    pub cusip: IdentifierCoverageStat,
    pub sedol: IdentifierCoverageStat,
    pub figi: IdentifierCoverageStat,
    pub lei: IdentifierCoverageStat,
}

// ─── Registry ────────────────────────────────────────────────────────

/// Asset Identifier Registry.
///
/// Loads a JSON registry of financial instruments and provides
/// indexed lookup methods for various identifier types.
#[derive(Debug, Clone)]
pub struct AssetRegistry {
    instruments: Vec<Instrument>,
    meta: RegistryMeta,
    path: PathBuf,

    // Lookup indices
    isin_index: HashMap<String, usize>,
    cusip_index: HashMap<String, usize>,
    sedol_index: HashMap<String, usize>,
    figi_index: HashMap<String, usize>,
    lei_index: HashMap<String, usize>,
    ticker_index: HashMap<String, Vec<usize>>,
    exchange_index: HashMap<String, Vec<usize>>,
    asset_class_index: HashMap<String, Vec<usize>>,
    country_index: HashMap<String, Vec<usize>>,
    currency_index: HashMap<String, Vec<usize>>,
}

impl AssetRegistry {
    /// Load the registry from a JSON file.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to `identifiers.json`
    ///
    /// # Errors
    ///
    /// Returns `RegistryError::FileRead` if the file cannot be read.
    /// Returns `RegistryError::InvalidJson` if the file is not valid JSON.
    ///
    /// # Example
    ///
    /// ```rust
    /// use asset_identifiers::AssetRegistry;
    ///
    /// let registry = AssetRegistry::load("../../identifiers.json")?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        let raw = fs::read_to_string(&path).map_err(|e| RegistryError::FileRead {
            path: path.display().to_string(),
            source: e,
        })?;

        let data: RegistryData =
            serde_json::from_str(&raw).map_err(|e| RegistryError::InvalidJson {
                path: path.display().to_string(),
                source: e,
            })?;

        Self::from_data(data, path)
    }

    /// Create a registry from parsed data.
    fn from_data(data: RegistryData, path: PathBuf) -> Result<Self> {
        let instruments = data.instruments;
        let meta = data.meta;

        let mut isin_index = HashMap::with_capacity(instruments.len());
        let mut cusip_index = HashMap::new();
        let mut sedol_index = HashMap::new();
        let mut figi_index = HashMap::new();
        let mut lei_index = HashMap::new();
        let mut ticker_index: HashMap<String, Vec<usize>> = HashMap::new();
        let mut exchange_index: HashMap<String, Vec<usize>> = HashMap::new();
        let mut asset_class_index: HashMap<String, Vec<usize>> = HashMap::new();
        let mut country_index: HashMap<String, Vec<usize>> = HashMap::new();
        let mut currency_index: HashMap<String, Vec<usize>> = HashMap::new();

        for (idx, inst) in instruments.iter().enumerate() {
            // ISIN
            let isin = inst.isin.to_uppercase();
            if isin_index.insert(isin.clone(), idx).is_some() {
                return Err(RegistryError::DuplicateIdentifier {
                    identifier_type: "ISIN",
                    value: isin,
                });
            }

            // CUSIP
            if let Some(cusip) = &inst.cusip {
                let cusip = cusip.to_uppercase();
                if cusip_index.insert(cusip.clone(), idx).is_some() {
                    return Err(RegistryError::DuplicateIdentifier {
                        identifier_type: "CUSIP",
                        value: cusip,
                    });
                }
            }

            // SEDOL
            if let Some(sedol) = &inst.sedol {
                let sedol = sedol.to_uppercase();
                if sedol_index.insert(sedol.clone(), idx).is_some() {
                    return Err(RegistryError::DuplicateIdentifier {
                        identifier_type: "SEDOL",
                        value: sedol,
                    });
                }
            }

            // FIGI
            if let Some(figi) = &inst.figi {
                let figi = figi.to_uppercase();
                if figi_index.insert(figi.clone(), idx).is_some() {
                    return Err(RegistryError::DuplicateIdentifier {
                        identifier_type: "FIGI",
                        value: figi,
                    });
                }
            }

            // LEI
            if let Some(lei) = &inst.lei {
                let lei = lei.to_uppercase();
                if lei_index.insert(lei.clone(), idx).is_some() {
                    return Err(RegistryError::DuplicateIdentifier {
                        identifier_type: "LEI",
                        value: lei,
                    });
                }
            }

            // Ticker
            let ticker = inst.ticker.to_uppercase();
            ticker_index.entry(ticker).or_default().push(idx);

            // Exchange
            let exchange = inst.exchange.to_uppercase();
            exchange_index.entry(exchange).or_default().push(idx);

            // Asset class
            let asset_class = format!("{:?}", inst.asset_class).to_lowercase();
            asset_class_index.entry(asset_class).or_default().push(idx);

            // Country
            if let Some(country) = &inst.country {
                let country = country.to_uppercase();
                country_index.entry(country).or_default().push(idx);
            }

            // Currency
            let currency = inst.currency.to_uppercase();
            currency_index.entry(currency).or_default().push(idx);
        }

        Ok(Self {
            instruments,
            meta,
            path,
            isin_index,
            cusip_index,
            sedol_index,
            figi_index,
            lei_index,
            ticker_index,
            exchange_index,
            asset_class_index,
            country_index,
            currency_index,
        })
    }

    // ─── Properties ──────────────────────────────────────────────────

    /// Number of instruments in the registry.
    pub fn count(&self) -> usize {
        self.instruments.len()
    }

    /// Path to the registry file.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Return registry metadata.
    pub fn meta(&self) -> &RegistryMeta {
        &self.meta
    }

    /// Return registry version.
    pub fn version(&self) -> &str {
        &self.meta.version
    }

    /// Return registry generation date.
    pub fn generated(&self) -> &str {
        &self.meta.generated
    }

    /// Return list of data sources.
    pub fn sources(&self) -> &[String] {
        &self.meta.sources
    }

    // ─── Bulk Access ─────────────────────────────────────────────────

    /// Return all instruments.
    pub fn all(&self) -> &[Instrument] {
        &self.instruments
    }

    /// Iterate over all instruments.
    pub fn iter(&self) -> std::slice::Iter<'_, Instrument> {
        self.instruments.iter()
    }

    // ─── Lookup by Identifier ────────────────────────────────────────

    /// Look up an instrument by ISIN.
    ///
    /// Returns `Some(&Instrument)` if found, `None` otherwise.
    pub fn by_isin(&self, isin: &str) -> Option<&Instrument> {
        self.isin_index
            .get(&isin.to_uppercase())
            .map(|&idx| &self.instruments[idx])
    }

    /// Look up an instrument by CUSIP.
    pub fn by_cusip(&self, cusip: &str) -> Option<&Instrument> {
        self.cusip_index
            .get(&cusip.to_uppercase())
            .map(|&idx| &self.instruments[idx])
    }

    /// Look up an instrument by SEDOL.
    pub fn by_sedol(&self, sedol: &str) -> Option<&Instrument> {
        self.sedol_index
            .get(&sedol.to_uppercase())
            .map(|&idx| &self.instruments[idx])
    }

    /// Look up an instrument by FIGI.
    pub fn by_figi(&self, figi: &str) -> Option<&Instrument> {
        self.figi_index
            .get(&figi.to_uppercase())
            .map(|&idx| &self.instruments[idx])
    }

    /// Look up an instrument by LEI.
    pub fn by_lei(&self, lei: &str) -> Option<&Instrument> {
        self.lei_index
            .get(&lei.to_uppercase())
            .map(|&idx| &self.instruments[idx])
    }

    // ─── Lookup by Ticker ────────────────────────────────────────────

    /// Look up instruments by ticker symbol.
    ///
    /// If `exchange` is `Some`, returns at most one instrument.
    /// If `exchange` is `None`, returns all matching instruments.
    ///
    /// # Warning: Ambiguous Tickers
    ///
    /// Some tickers are ambiguous — the same symbol exists on multiple
    /// exchanges. "PRU" is Prudential plc (XLON) and Prudential Financial
    /// (XNYS). Always use the `exchange` parameter when the ticker might
    /// be ambiguous. Use [`tickers_with_multiple_listings`] to detect
    /// ambiguous tickers before calling without an exchange.
    ///
    /// # Example
    ///
    /// ```rust
    /// use asset_identifiers::AssetRegistry;
    ///
    /// let registry = AssetRegistry::load("../../identifiers.json")?;
    ///
    /// // Single result with exchange (recommended)
    /// let aapl = registry.by_ticker("AAPL", Some("XNAS"));
    /// assert_eq!(aapl.len(), 1);
    ///
    /// // Multiple results without exchange (use with caution)
    /// let pru = registry.by_ticker("PRU", None);
    /// assert_eq!(pru.len(), 2);
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn by_ticker(&self, ticker: &str, exchange: Option<&str>) -> Vec<&Instrument> {
        let indices = self
            .ticker_index
            .get(&ticker.to_uppercase())
            .map(|v| v.as_slice())
            .unwrap_or(&[]);

        match exchange {
            Some(exch) => {
                let exch = exch.to_uppercase();
                indices
                    .iter()
                    .filter(|&&idx| self.instruments[idx].exchange == exch)
                    .map(|&idx| &self.instruments[idx])
                    .collect()
            }
            None => indices.iter().map(|&idx| &self.instruments[idx]).collect(),
        }
    }

    /// Look up a single instrument by ticker and exchange.
    ///
    /// Returns `Some(&Instrument)` if exactly one match is found.
    pub fn by_ticker_exchange(&self, ticker: &str, exchange: &str) -> Option<&Instrument> {
        let results = self.by_ticker(ticker, Some(exchange));
        results.into_iter().next()
    }

    // ─── Filtering ───────────────────────────────────────────────────

    /// Return all instruments on a given exchange.
    pub fn by_exchange(&self, exchange: &str) -> Vec<&Instrument> {
        self.exchange_index
            .get(&exchange.to_uppercase())
            .map(|v| v.iter().map(|&idx| &self.instruments[idx]).collect())
            .unwrap_or_default()
    }

    /// Return all instruments of a given asset class.
    pub fn by_asset_class(&self, asset_class: AssetClass) -> Vec<&Instrument> {
        let key = format!("{:?}", asset_class).to_lowercase();
        self.asset_class_index
            .get(&key)
            .map(|v| v.iter().map(|&idx| &self.instruments[idx]).collect())
            .unwrap_or_default()
    }

    /// Return all instruments from a given country.
    pub fn by_country(&self, country: &str) -> Vec<&Instrument> {
        self.country_index
            .get(&country.to_uppercase())
            .map(|v| v.iter().map(|&idx| &self.instruments[idx]).collect())
            .unwrap_or_default()
    }

    /// Return all instruments trading in a given currency.
    pub fn by_currency(&self, currency: &str) -> Vec<&Instrument> {
        self.currency_index
            .get(&currency.to_uppercase())
            .map(|v| v.iter().map(|&idx| &self.instruments[idx]).collect())
            .unwrap_or_default()
    }

    // ─── Aggregate Information ───────────────────────────────────────

    /// Return sorted list of all exchanges.
    pub fn exchanges(&self) -> Vec<&str> {
        let mut keys: Vec<&str> = self.exchange_index.keys().map(|s| s.as_str()).collect();
        keys.sort();
        keys
    }

    /// Return sorted list of all asset classes.
    pub fn asset_classes(&self) -> Vec<AssetClass> {
        let mut classes: Vec<AssetClass> = self
            .asset_class_index
            .keys()
            .map(|k| match k.as_str() {
                "equity" => AssetClass::Equity,
                "etf" => AssetClass::Etf,
                "bond" => AssetClass::Bond,
                "option" => AssetClass::Option,
                "future" => AssetClass::Future,
                _ => AssetClass::Other,
            })
            .collect();
        classes.sort_by_key(|c| format!("{:?}", c));
        classes
    }

    /// Return sorted list of all currencies.
    pub fn currencies(&self) -> Vec<&str> {
        let mut keys: Vec<&str> = self.currency_index.keys().map(|s| s.as_str()).collect();
        keys.sort();
        keys
    }

    /// Return sorted list of all countries.
    pub fn countries(&self) -> Vec<&str> {
        let mut keys: Vec<&str> = self.country_index.keys().map(|s| s.as_str()).collect();
        keys.sort();
        keys
    }

    // ─── Convenience Methods ─────────────────────────────────────────

    /// Check if an ISIN exists in the registry.
    pub fn isin_exists(&self, isin: &str) -> bool {
        self.by_isin(isin).is_some()
    }

    /// Check if a ticker exists in the registry.
    pub fn ticker_exists(&self, ticker: &str, exchange: Option<&str>) -> bool {
        !self.by_ticker(ticker, exchange).is_empty()
    }

    /// Return identifier coverage statistics.
    pub fn identifier_coverage(&self) -> IdentifierCoverage {
        let total = self.count();

        let calc = |covered: usize| IdentifierCoverageStat {
            covered,
            total,
            percentage: if total > 0 {
                (covered as f64 / total as f64) * 100.0
            } else {
                0.0
            },
        };

        IdentifierCoverage {
            isin: calc(
                self.instruments
                    .iter()
                    .filter(|i| !i.isin.is_empty())
                    .count(),
            ),
            cusip: calc(
                self.instruments
                    .iter()
                    .filter(|i| i.cusip.is_some())
                    .count(),
            ),
            sedol: calc(
                self.instruments
                    .iter()
                    .filter(|i| i.sedol.is_some())
                    .count(),
            ),
            figi: calc(self.instruments.iter().filter(|i| i.figi.is_some()).count()),
            lei: calc(self.instruments.iter().filter(|i| i.lei.is_some()).count()),
        }
    }

    /// Return tickers that appear on multiple exchanges.
    pub fn tickers_with_multiple_listings(&self) -> Vec<&str> {
        let mut ambiguous: Vec<&str> = self
            .ticker_index
            .iter()
            .filter(|(_, v)| v.len() > 1)
            .map(|(k, _)| k.as_str())
            .collect();
        ambiguous.sort();
        ambiguous
    }
}

impl std::fmt::Display for AssetRegistry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Asset Identifier Registry v{} ({} instruments)",
            self.version(),
            self.count()
        )
    }
}

impl<'a> IntoIterator for &'a AssetRegistry {
    type Item = &'a Instrument;
    type IntoIter = std::slice::Iter<'a, Instrument>;

    fn into_iter(self) -> Self::IntoIter {
        self.instruments.iter()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_registry() -> AssetRegistry {
        AssetRegistry::load("../../identifiers.json").expect("Failed to load test registry")
    }

    #[test]
    fn test_count() {
        let registry = test_registry();
        assert_eq!(registry.count(), 50);
    }

    #[test]
    fn test_by_isin() {
        let registry = test_registry();
        let aapl = registry.by_isin("US0378331005").unwrap();
        assert_eq!(aapl.ticker, "AAPL");
        assert_eq!(aapl.name, "Apple Inc.");
    }

    #[test]
    fn test_by_cusip() {
        let registry = test_registry();
        let msft = registry.by_cusip("594918104").unwrap();
        assert_eq!(msft.ticker, "MSFT");
    }

    #[test]
    fn test_by_figi() {
        let registry = test_registry();
        let aapl = registry.by_figi("BBG000B9XRY4").unwrap();
        assert_eq!(aapl.isin, "US0378331005");
    }

    #[test]
    fn test_by_ticker_with_exchange() {
        let registry = test_registry();
        let results = registry.by_ticker("AAPL", Some("XNAS"));
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].isin, "US0378331005");
    }

    #[test]
    fn test_by_ticker_ambiguous() {
        let registry = test_registry();
        let pru = registry.by_ticker("PRU", None);
        assert_eq!(pru.len(), 2);
    }

    #[test]
    fn test_by_ticker_nonexistent() {
        let registry = test_registry();
        assert_eq!(registry.by_ticker("ZZZZ", None).len(), 0);
    }

    #[test]
    fn test_filter_by_exchange() {
        let registry = test_registry();
        let xnas = registry.by_exchange("XNAS");
        assert!(!xnas.is_empty());
        for inst in &xnas {
            assert_eq!(inst.exchange, "XNAS");
        }
    }

    #[test]
    fn test_filter_by_asset_class() {
        let registry = test_registry();
        let etfs = registry.by_asset_class(AssetClass::Etf);
        assert!(!etfs.is_empty());
    }

    #[test]
    fn test_metadata() {
        let registry = test_registry();
        assert_eq!(registry.version(), "1.0.0");
        assert_eq!(registry.count(), 50);
    }

    #[test]
    fn test_exchanges() {
        let registry = test_registry();
        let exchanges = registry.exchanges();
        assert!(exchanges.contains(&"XNAS"));
        assert!(exchanges.contains(&"XNYS"));
        assert_eq!(exchanges.len(), 9);
    }

    #[test]
    fn test_ticker_change_preserved() {
        let registry = test_registry();
        let meta = registry.by_isin("US30303M1027").unwrap();
        assert_eq!(meta.ticker, "META");
        let tickers: Vec<&str> = meta.history.iter().map(|h| h.ticker.as_str()).collect();
        assert!(tickers.contains(&"FB"));
        assert!(tickers.contains(&"META"));
    }

    #[test]
    fn test_multi_exchange_listing() {
        let registry = test_registry();
        let aapl = registry.by_isin("US0378331005").unwrap();
        let exchanges: Vec<&str> = aapl.listings.iter().map(|l| l.exchange.as_str()).collect();
        assert!(exchanges.contains(&"XNAS"));
        assert!(exchanges.contains(&"XETR"));
    }

    #[test]
    fn test_identifier_coverage() {
        let registry = test_registry();
        let coverage = registry.identifier_coverage();
        assert_eq!(coverage.isin.covered, 50);
        assert_eq!(coverage.isin.percentage, 100.0);
    }

    #[test]
    fn test_tickers_with_multiple_listings() {
        let registry = test_registry();
        let ambiguous = registry.tickers_with_multiple_listings();
        assert!(ambiguous.contains(&"PRU"));
    }

    #[test]
    fn test_iterator() {
        let registry = test_registry();
        let count = registry.iter().count();
        assert_eq!(count, 50);
    }
}
