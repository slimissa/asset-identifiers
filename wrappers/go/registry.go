// Package assetidentifiers provides a lightweight interface to the
// canonical asset identifier registry (identifiers.json).
//
// Example:
//
//	registry, err := assetidentifiers.LoadRegistry("identifiers.json")
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	aapl, ok := registry.ByIsin("US0378331005")
//	if ok {
//		fmt.Println(aapl.Ticker) // AAPL
//	}
package assetidentifiers

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// ─── Error Types ─────────────────────────────────────────────────────

// RegistryError represents an error that occurred while loading
// or querying the registry.
type RegistryError struct {
	Op  string // Operation that failed
	Err error  // Underlying error
}

func (e *RegistryError) Error() string {
	return fmt.Sprintf("asset-identifiers: %s: %v", e.Op, e.Err)
}

func (e *RegistryError) Unwrap() error {
	return e.Err
}

// ─── Data Types ──────────────────────────────────────────────────────

// AssetClass represents the type of financial instrument.
type AssetClass string

// Asset class constants.
const (
	AssetClassEquity AssetClass = "equity"
	AssetClassEtf    AssetClass = "etf"
	AssetClassBond   AssetClass = "bond"
	AssetClassOption AssetClass = "option"
	AssetClassFuture AssetClass = "future"
	AssetClassOther  AssetClass = "other"
)

// ListingStatus represents the status of an exchange listing.
type ListingStatus string

// Listing status constants.
const (
	ListingStatusPrimary          ListingStatus = "PRIMARY"
	ListingStatusSecondary        ListingStatus = "SECONDARY"
	ListingStatusDepositaryReceipt ListingStatus = "DEPOSITARY_RECEIPT"
	ListingStatusDelisted         ListingStatus = "DELISTED"
)

// CorporateActionType represents the type of corporate action.
type CorporateActionType string

// Corporate action type constants.
const (
	CorporateActionSplit         CorporateActionType = "SPLIT"
	CorporateActionReverseSplit  CorporateActionType = "REVERSE_SPLIT"
	CorporateActionDividend      CorporateActionType = "DIVIDEND"
	CorporateActionSpinoff       CorporateActionType = "SPINOFF"
	CorporateActionMerger        CorporateActionType = "MERGER"
	CorporateActionAcquisition   CorporateActionType = "ACQUISITION"
	CorporateActionRightsIssue   CorporateActionType = "RIGHTS_ISSUE"
	CorporateActionBuyback       CorporateActionType = "BUYBACK"
)

// ChangeType represents the type of ticker change event.
type ChangeType string

// Ticker change type constants.
const (
	ChangeTypeNone          ChangeType = "none"
	ChangeTypeRename        ChangeType = "rename"
	ChangeTypeDelisting     ChangeType = "delisting"
	ChangeTypeRelisting     ChangeType = "relisting"
	ChangeTypeMerger        ChangeType = "merger"
	ChangeTypeAcquisition   ChangeType = "acquisition"
	ChangeTypeSpinoff       ChangeType = "spinoff"
	ChangeTypeSplit         ChangeType = "split"
	ChangeTypeReverseSplit  ChangeType = "reverse_split"
)

// ExchangeListing represents a listing on a specific exchange.
type ExchangeListing struct {
	Exchange      string        `json:"exchange"`
	Ticker        string        `json:"ticker"`
	Currency      string        `json:"currency"`
	Status        ListingStatus `json:"status"`
	ListingDate   *string       `json:"listing_date,omitempty"`
	DelistingDate *string       `json:"delisting_date,omitempty"`
}

// HistoryEvent represents a ticker change event.
type HistoryEvent struct {
	Ticker     string     `json:"ticker"`
	ChangeDate string     `json:"change_date"`
	ChangeType ChangeType `json:"change_type"`
	Reason     *string    `json:"reason,omitempty"`
	Source     *string    `json:"source,omitempty"`
	SourceURL  *string    `json:"source_url,omitempty"`
}

// CorporateAction represents a corporate action event.
type CorporateAction struct {
	Date       string              `json:"date"`
	ActionType CorporateActionType `json:"action_type"`
	Ratio      *string             `json:"ratio,omitempty"`
	Details    *string             `json:"details,omitempty"`
	Source     *string             `json:"source,omitempty"`
	SourceURL  *string             `json:"source_url,omitempty"`
}

// Instrument represents a financial instrument.
type Instrument struct {
	Isin             string             `json:"isin"`
	Cusip            *string            `json:"cusip,omitempty"`
	Sedol            *string            `json:"sedol,omitempty"`
	Figi             *string            `json:"figi,omitempty"`
	Lei              *string            `json:"lei,omitempty"`
	Ticker           string             `json:"ticker"`
	Exchange         string             `json:"exchange"`
	Name             string             `json:"name"`
	Currency         string             `json:"currency"`
	AssetClass       AssetClass         `json:"asset_class"`
	InstrumentType   *string            `json:"instrument_type,omitempty"`
	Sector           *string            `json:"sector,omitempty"`
	Industry         *string            `json:"industry,omitempty"`
	Country          *string            `json:"country,omitempty"`
	Active           bool               `json:"active"`
	ListingDate      *string            `json:"listing_date,omitempty"`
	DelistingDate    *string            `json:"delisting_date,omitempty"`
	Listings         []ExchangeListing  `json:"listings,omitempty"`
	History          []HistoryEvent     `json:"history,omitempty"`
	CorporateActions []CorporateAction  `json:"corporate_actions,omitempty"`
}

// RegistryCoverage represents registry coverage information.
type RegistryCoverage struct {
	Exchanges    []string `json:"exchanges,omitempty"`
	AssetClasses []string `json:"asset_classes,omitempty"`
	Countries    []string `json:"countries,omitempty"`
}

// RegistryMeta represents registry metadata.
type RegistryMeta struct {
	Version        string           `json:"version"`
	Generated      string           `json:"generated"`
	Count          int              `json:"count"`
	Sources        []string         `json:"sources,omitempty"`
	Coverage       RegistryCoverage `json:"coverage,omitempty"`
	BuildTimestamp *string          `json:"build_timestamp,omitempty"`
}

// registryData is the top-level structure of identifiers.json.
type registryData struct {
	Meta        RegistryMeta `json:"meta"`
	Instruments []Instrument `json:"instruments"`
}

// IdentifierCoverageStat represents coverage for a single identifier type.
type IdentifierCoverageStat struct {
	Covered    int     `json:"covered"`
	Total      int     `json:"total"`
	Percentage float64 `json:"percentage"`
}

// IdentifierCoverage represents coverage for all identifier types.
type IdentifierCoverage struct {
	Isin  IdentifierCoverageStat `json:"isin"`
	Cusip IdentifierCoverageStat `json:"cusip"`
	Sedol IdentifierCoverageStat `json:"sedol"`
	Figi  IdentifierCoverageStat `json:"figi"`
	Lei   IdentifierCoverageStat `json:"lei"`
}

// ─── Registry ────────────────────────────────────────────────────────

// AssetRegistry represents the loaded asset identifier registry.
type AssetRegistry struct {
	instruments []Instrument
	meta        RegistryMeta
	path        string

	// Lookup indices
	isinIndex    map[string]int
	cusipIndex   map[string]int
	sedolIndex   map[string]int
	figiIndex    map[string]int
	leiIndex     map[string]int
	tickerIndex  map[string][]int
	exchangeIndex map[string][]int
	assetClassIndex map[string][]int
	countryIndex map[string][]int
	currencyIndex map[string][]int
}

// LoadRegistry loads the registry from a JSON file.
//
// Returns an error if the file cannot be read or parsed, or if
// duplicate identifiers are found.
func LoadRegistry(path string) (*AssetRegistry, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, &RegistryError{Op: "read file", Err: err}
	}

	var data registryData
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, &RegistryError{Op: "parse JSON", Err: err}
	}

	return newRegistry(data, path)
}

// newRegistry creates a registry from parsed data and builds indices.
func newRegistry(data registryData, path string) (*AssetRegistry, error) {
	absPath, _ := filepath.Abs(path)

	registry := &AssetRegistry{
		instruments:     data.Instruments,
		meta:            data.Meta,
		path:            absPath,
		isinIndex:       make(map[string]int, len(data.Instruments)),
		cusipIndex:      make(map[string]int),
		sedolIndex:      make(map[string]int),
		figiIndex:       make(map[string]int),
		leiIndex:        make(map[string]int),
		tickerIndex:     make(map[string][]int),
		exchangeIndex:   make(map[string][]int),
		assetClassIndex: make(map[string][]int),
		countryIndex:    make(map[string][]int),
		currencyIndex:   make(map[string][]int),
	}

	for idx := range data.Instruments {
		inst := &data.Instruments[idx]

		// ISIN
		isin := strings.ToUpper(inst.Isin)
		if _, exists := registry.isinIndex[isin]; exists {
			return nil, &RegistryError{Op: "duplicate ISIN", Err: fmt.Errorf("%s", isin)}
		}
		registry.isinIndex[isin] = idx

		// CUSIP
		if inst.Cusip != nil {
			cusip := strings.ToUpper(*inst.Cusip)
			if _, exists := registry.cusipIndex[cusip]; exists {
				return nil, &RegistryError{Op: "duplicate CUSIP", Err: fmt.Errorf("%s", cusip)}
			}
			registry.cusipIndex[cusip] = idx
		}

		// SEDOL
		if inst.Sedol != nil {
			sedol := strings.ToUpper(*inst.Sedol)
			if _, exists := registry.sedolIndex[sedol]; exists {
				return nil, &RegistryError{Op: "duplicate SEDOL", Err: fmt.Errorf("%s", sedol)}
			}
			registry.sedolIndex[sedol] = idx
		}

		// FIGI
		if inst.Figi != nil {
			figi := strings.ToUpper(*inst.Figi)
			if _, exists := registry.figiIndex[figi]; exists {
				return nil, &RegistryError{Op: "duplicate FIGI", Err: fmt.Errorf("%s", figi)}
			}
			registry.figiIndex[figi] = idx
		}

		// LEI
		if inst.Lei != nil {
			lei := strings.ToUpper(*inst.Lei)
			if _, exists := registry.leiIndex[lei]; exists {
				return nil, &RegistryError{Op: "duplicate LEI", Err: fmt.Errorf("%s", lei)}
			}
			registry.leiIndex[lei] = idx
		}

		// Ticker
		ticker := strings.ToUpper(inst.Ticker)
		registry.tickerIndex[ticker] = append(registry.tickerIndex[ticker], idx)

		// Exchange
		exchange := strings.ToUpper(inst.Exchange)
		registry.exchangeIndex[exchange] = append(registry.exchangeIndex[exchange], idx)

		// Asset class
		assetClass := string(inst.AssetClass)
		registry.assetClassIndex[assetClass] = append(registry.assetClassIndex[assetClass], idx)

		// Country
		if inst.Country != nil {
			country := strings.ToUpper(*inst.Country)
			registry.countryIndex[country] = append(registry.countryIndex[country], idx)
		}

		// Currency
		currency := strings.ToUpper(inst.Currency)
		registry.currencyIndex[currency] = append(registry.currencyIndex[currency], idx)
	}

	return registry, nil
}

// ─── Properties ──────────────────────────────────────────────────────

// Count returns the number of instruments in the registry.
func (r *AssetRegistry) Count() int {
	return len(r.instruments)
}

// Path returns the absolute path to the registry file.
func (r *AssetRegistry) Path() string {
	return r.path
}

// Meta returns the registry metadata.
func (r *AssetRegistry) Meta() *RegistryMeta {
	return &r.meta
}

// Version returns the registry version.
func (r *AssetRegistry) Version() string {
	return r.meta.Version
}

// Generated returns the registry generation date.
func (r *AssetRegistry) Generated() string {
	return r.meta.Generated
}

// Sources returns the list of data sources.
func (r *AssetRegistry) Sources() []string {
	return r.meta.Sources
}

// ─── Bulk Access ─────────────────────────────────────────────────────

// All returns all instruments.
func (r *AssetRegistry) All() []Instrument {
	return r.instruments
}

// Instruments returns a pointer to the instruments slice.
func (r *AssetRegistry) Instruments() *[]Instrument {
	return &r.instruments
}

// ─── Lookup by Identifier ────────────────────────────────────────────

// ByIsin looks up an instrument by ISIN.
// Returns the instrument and true if found.
func (r *AssetRegistry) ByIsin(isin string) (*Instrument, bool) {
	idx, ok := r.isinIndex[strings.ToUpper(isin)]
	if !ok {
		return nil, false
	}
	return &r.instruments[idx], true
}

// ByCusip looks up an instrument by CUSIP.
func (r *AssetRegistry) ByCusip(cusip string) (*Instrument, bool) {
	idx, ok := r.cusipIndex[strings.ToUpper(cusip)]
	if !ok {
		return nil, false
	}
	return &r.instruments[idx], true
}

// BySedol looks up an instrument by SEDOL.
func (r *AssetRegistry) BySedol(sedol string) (*Instrument, bool) {
	idx, ok := r.sedolIndex[strings.ToUpper(sedol)]
	if !ok {
		return nil, false
	}
	return &r.instruments[idx], true
}

// ByFigi looks up an instrument by FIGI.
func (r *AssetRegistry) ByFigi(figi string) (*Instrument, bool) {
	idx, ok := r.figiIndex[strings.ToUpper(figi)]
	if !ok {
		return nil, false
	}
	return &r.instruments[idx], true
}

// ByLei looks up an instrument by LEI.
func (r *AssetRegistry) ByLei(lei string) (*Instrument, bool) {
	idx, ok := r.leiIndex[strings.ToUpper(lei)]
	if !ok {
		return nil, false
	}
	return &r.instruments[idx], true
}

// ─── Lookup by Ticker ────────────────────────────────────────────────

// ByTicker looks up instruments by ticker symbol.
//
// If exchange is non-empty, returns at most one instrument.
// If exchange is empty, returns all matching instruments.
func (r *AssetRegistry) ByTicker(ticker string, exchange string) []*Instrument {
	indices, ok := r.tickerIndex[strings.ToUpper(ticker)]
	if !ok {
		return nil
	}

	if exchange == "" {
		result := make([]*Instrument, 0, len(indices))
		for _, idx := range indices {
			result = append(result, &r.instruments[idx])
		}
		return result
	}

	exchangeUpper := strings.ToUpper(exchange)
	for _, idx := range indices {
		if strings.EqualFold(r.instruments[idx].Exchange, exchangeUpper) {
			return []*Instrument{&r.instruments[idx]}
		}
	}
	return nil
}

// ByTickerExchange looks up a single instrument by ticker and exchange.
func (r *AssetRegistry) ByTickerExchange(ticker string, exchange string) (*Instrument, bool) {
	results := r.ByTicker(ticker, exchange)
	if len(results) == 1 {
		return results[0], true
	}
	return nil, false
}

// ─── Filtering ───────────────────────────────────────────────────────

// ByExchange returns all instruments on a given exchange.
func (r *AssetRegistry) ByExchange(exchange string) []*Instrument {
	indices, ok := r.exchangeIndex[strings.ToUpper(exchange)]
	if !ok {
		return nil
	}
	result := make([]*Instrument, 0, len(indices))
	for _, idx := range indices {
		result = append(result, &r.instruments[idx])
	}
	return result
}

// ByAssetClass returns all instruments of a given asset class.
func (r *AssetRegistry) ByAssetClass(assetClass AssetClass) []*Instrument {
	indices, ok := r.assetClassIndex[string(assetClass)]
	if !ok {
		return nil
	}
	result := make([]*Instrument, 0, len(indices))
	for _, idx := range indices {
		result = append(result, &r.instruments[idx])
	}
	return result
}

// ByCountry returns all instruments from a given country.
func (r *AssetRegistry) ByCountry(country string) []*Instrument {
	indices, ok := r.countryIndex[strings.ToUpper(country)]
	if !ok {
		return nil
	}
	result := make([]*Instrument, 0, len(indices))
	for _, idx := range indices {
		result = append(result, &r.instruments[idx])
	}
	return result
}

// ByCurrency returns all instruments trading in a given currency.
func (r *AssetRegistry) ByCurrency(currency string) []*Instrument {
	indices, ok := r.currencyIndex[strings.ToUpper(currency)]
	if !ok {
		return nil
	}
	result := make([]*Instrument, 0, len(indices))
	for _, idx := range indices {
		result = append(result, &r.instruments[idx])
	}
	return result
}

// ─── Aggregate Information ───────────────────────────────────────────

// Exchanges returns a sorted list of all exchanges.
func (r *AssetRegistry) Exchanges() []string {
	keys := make([]string, 0, len(r.exchangeIndex))
	for k := range r.exchangeIndex {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// AssetClasses returns a sorted list of all asset classes.
func (r *AssetRegistry) AssetClasses() []AssetClass {
	keys := make([]string, 0, len(r.assetClassIndex))
	for k := range r.assetClassIndex {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	classes := make([]AssetClass, 0, len(keys))
	for _, k := range keys {
		classes = append(classes, AssetClass(k))
	}
	return classes
}

// Currencies returns a sorted list of all currencies.
func (r *AssetRegistry) Currencies() []string {
	keys := make([]string, 0, len(r.currencyIndex))
	for k := range r.currencyIndex {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// Countries returns a sorted list of all countries.
func (r *AssetRegistry) Countries() []string {
	keys := make([]string, 0, len(r.countryIndex))
	for k := range r.countryIndex {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// ─── Convenience Methods ─────────────────────────────────────────────

// IsinExists checks if an ISIN exists in the registry.
func (r *AssetRegistry) IsinExists(isin string) bool {
	_, ok := r.ByIsin(isin)
	return ok
}

// TickerExists checks if a ticker exists in the registry.
func (r *AssetRegistry) TickerExists(ticker string, exchange string) bool {
	return len(r.ByTicker(ticker, exchange)) > 0
}

// IdentifierCoverage returns coverage statistics for each identifier type.
func (r *AssetRegistry) IdentifierCoverage() IdentifierCoverage {
	total := r.Count()

	calc := func(covered int) IdentifierCoverageStat {
		percentage := 0.0
		if total > 0 {
			percentage = float64(covered) / float64(total) * 100.0
		}
		return IdentifierCoverageStat{
			Covered:    covered,
			Total:      total,
			Percentage: percentage,
		}
	}

	isinCovered := 0
	cusipCovered := 0
	sedolCovered := 0
	figiCovered := 0
	leiCovered := 0

	for i := range r.instruments {
		if r.instruments[i].Isin != "" {
			isinCovered++
		}
		if r.instruments[i].Cusip != nil {
			cusipCovered++
		}
		if r.instruments[i].Sedol != nil {
			sedolCovered++
		}
		if r.instruments[i].Figi != nil {
			figiCovered++
		}
		if r.instruments[i].Lei != nil {
			leiCovered++
		}
	}

	return IdentifierCoverage{
		Isin:  calc(isinCovered),
		Cusip: calc(cusipCovered),
		Sedol: calc(sedolCovered),
		Figi:  calc(figiCovered),
		Lei:   calc(leiCovered),
	}
}

// TickersWithMultipleListings returns tickers that appear on multiple exchanges.
func (r *AssetRegistry) TickersWithMultipleListings() []string {
	var ambiguous []string
	for ticker, indices := range r.tickerIndex {
		if len(indices) > 1 {
			ambiguous = append(ambiguous, ticker)
		}
	}
	sort.Strings(ambiguous)
	return ambiguous
}

// ─── String Representation ───────────────────────────────────────────

// String returns a human-readable representation of the registry.
func (r *AssetRegistry) String() string {
	return fmt.Sprintf("Asset Identifier Registry v%s (%d instruments)", r.Version(), r.Count())
}