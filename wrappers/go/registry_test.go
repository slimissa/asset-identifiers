package assetidentifiers

import (
	"os"
	"path/filepath"
	"testing"
)

// ─── Test Setup ──────────────────────────────────────────────────────

// testRegistry loads the registry once for all tests.
var testRegistry = loadTestRegistry()

func loadTestRegistry() *AssetRegistry {
	// Path: wrappers/go/ → ../../identifiers.json
	registryPath := filepath.Join("..", "..", "identifiers.json")
	registry, err := LoadRegistry(registryPath)
	if err != nil {
		panic("Failed to load test registry: " + err.Error())
	}
	return registry
}

// ─── Registry Loading Tests ──────────────────────────────────────────

func TestRegistryLoads(t *testing.T) {
	if testRegistry == nil {
		t.Fatal("Registry should not be nil")
	}
}

func TestRegistryCount(t *testing.T) {
	if testRegistry.Count() != 50 {
		t.Errorf("Expected count 50, got %d", testRegistry.Count())
	}
}

func TestRegistryPath(t *testing.T) {
	path := testRegistry.Path()
	if path == "" {
		t.Error("Path should not be empty")
	}
}

func TestRegistryVersion(t *testing.T) {
	if testRegistry.Version() != "1.0.0" {
		t.Errorf("Expected version 1.0.0, got %s", testRegistry.Version())
	}
}

func TestRegistryMeta(t *testing.T) {
	meta := testRegistry.Meta()
	if meta == nil {
		t.Fatal("Meta should not be nil")
	}
	if meta.Count != 50 {
		t.Errorf("Expected meta.count 50, got %d", meta.Count)
	}
	if meta.Version != "1.0.0" {
		t.Errorf("Expected meta.version 1.0.0, got %s", meta.Version)
	}
}

// ─── ISIN Lookup Tests ───────────────────────────────────────────────

func TestByIsinFound(t *testing.T) {
	aapl, ok := testRegistry.ByIsin("US0378331005")
	if !ok {
		t.Fatal("Expected AAPL to be found by ISIN")
	}
	if aapl.Ticker != "AAPL" {
		t.Errorf("Expected ticker AAPL, got %s", aapl.Ticker)
	}
	if aapl.Name != "Apple Inc." {
		t.Errorf("Expected name 'Apple Inc.', got %s", aapl.Name)
	}
	if aapl.Currency != "USD" {
		t.Errorf("Expected currency USD, got %s", aapl.Currency)
	}
	if aapl.Exchange != "XNAS" {
		t.Errorf("Expected exchange XNAS, got %s", aapl.Exchange)
	}
}

func TestByIsinNotFound(t *testing.T) {
	_, ok := testRegistry.ByIsin("XX0000000000")
	if ok {
		t.Error("Expected XX0000000000 to not be found")
	}
}

func TestByIsinCaseInsensitive(t *testing.T) {
	aapl, ok := testRegistry.ByIsin("us0378331005")
	if !ok {
		t.Fatal("Expected lowercase ISIN to be found")
	}
	if aapl.Ticker != "AAPL" {
		t.Errorf("Expected AAPL, got %s", aapl.Ticker)
	}
}

func TestByIsinInternational(t *testing.T) {
	sony, ok := testRegistry.ByIsin("JP3435000009")
	if !ok {
		t.Fatal("Expected Sony to be found")
	}
	if sony.Ticker != "7203" {
		t.Errorf("Expected ticker 7203, got %s", sony.Ticker)
	}
	if sony.Currency != "JPY" {
		t.Errorf("Expected currency JPY, got %s", sony.Currency)
	}
}

// ─── CUSIP Lookup Tests ──────────────────────────────────────────────

func TestByCusipFound(t *testing.T) {
	aapl, ok := testRegistry.ByCusip("037833100")
	if !ok {
		t.Fatal("Expected AAPL to be found by CUSIP")
	}
	if aapl.Isin != "US0378331005" {
		t.Errorf("Expected ISIN US0378331005, got %s", aapl.Isin)
	}
}

func TestByCusipNotFound(t *testing.T) {
	_, ok := testRegistry.ByCusip("000000000")
	if ok {
		t.Error("Expected 000000000 to not be found")
	}
}

// ─── FIGI Lookup Tests ───────────────────────────────────────────────

func TestByFigiFound(t *testing.T) {
	aapl, ok := testRegistry.ByFigi("BBG000B9XRY4")
	if !ok {
		t.Fatal("Expected AAPL to be found by FIGI")
	}
	if aapl.Isin != "US0378331005" {
		t.Errorf("Expected ISIN US0378331005, got %s", aapl.Isin)
	}
}

func TestByFigiNotFound(t *testing.T) {
	_, ok := testRegistry.ByFigi("BBG00000000")
	if ok {
		t.Error("Expected BBG00000000 to not be found")
	}
}

// ─── LEI Lookup Tests ────────────────────────────────────────────────

func TestByLeiFound(t *testing.T) {
	aapl, ok := testRegistry.ByLei("HWUPKR0MPOU8FGXBT394")
	if !ok {
		t.Fatal("Expected AAPL to be found by LEI")
	}
	if aapl.Ticker != "AAPL" {
		t.Errorf("Expected AAPL, got %s", aapl.Ticker)
	}
}

func TestByLeiNotFound(t *testing.T) {
	_, ok := testRegistry.ByLei("00000000000000000000")
	if ok {
		t.Error("Expected LEI to not be found")
	}
}

// ─── Ticker Lookup Tests ─────────────────────────────────────────────

func TestByTickerWithExchange(t *testing.T) {
	results := testRegistry.ByTicker("AAPL", "XNAS")
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Isin != "US0378331005" {
		t.Errorf("Expected ISIN US0378331005, got %s", results[0].Isin)
	}
}

func TestByTickerWithoutExchange(t *testing.T) {
	results := testRegistry.ByTicker("AAPL", "")
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Ticker != "AAPL" {
		t.Errorf("Expected AAPL, got %s", results[0].Ticker)
	}
}

func TestByTickerAmbiguous(t *testing.T) {
	results := testRegistry.ByTicker("PRU", "")
	if len(results) != 2 {
		t.Fatalf("Expected 2 results for PRU, got %d", len(results))
	}

	// Verify both exchanges
	exchanges := make([]string, 0, 2)
	for _, inst := range results {
		exchanges = append(exchanges, inst.Exchange)
	}

	foundXLON := false
	foundXNYS := false
	for _, e := range exchanges {
		if e == "XLON" {
			foundXLON = true
		}
		if e == "XNYS" {
			foundXNYS = true
		}
	}

	if !foundXLON || !foundXNYS {
		t.Errorf("Expected XLON and XNYS, got %v", exchanges)
	}
}

func TestByTickerDisambiguateLondon(t *testing.T) {
	results := testRegistry.ByTicker("PRU", "XLON")
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Isin != "GB0007099541" {
		t.Errorf("Expected ISIN GB0007099541, got %s", results[0].Isin)
	}
	if results[0].Currency != "GBP" {
		t.Errorf("Expected GBP, got %s", results[0].Currency)
	}
}

func TestByTickerDisambiguateNewYork(t *testing.T) {
	results := testRegistry.ByTicker("PRU", "XNYS")
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Isin != "US7443201022" {
		t.Errorf("Expected ISIN US7443201022, got %s", results[0].Isin)
	}
	if results[0].Currency != "USD" {
		t.Errorf("Expected USD, got %s", results[0].Currency)
	}
}

func TestByTickerNotFound(t *testing.T) {
	results := testRegistry.ByTicker("ZZZZ", "")
	if len(results) != 0 {
		t.Errorf("Expected 0 results, got %d", len(results))
	}
}

func TestByTickerNotFoundWithExchange(t *testing.T) {
	results := testRegistry.ByTicker("ZZZZ", "XNAS")
	if len(results) != 0 {
		t.Errorf("Expected 0 results, got %d", len(results))
	}
}

func TestByTickerExchangeConvenience(t *testing.T) {
	aapl, ok := testRegistry.ByTickerExchange("AAPL", "XNAS")
	if !ok {
		t.Fatal("Expected AAPL to be found")
	}
	if aapl.Isin != "US0378331005" {
		t.Errorf("Expected US0378331005, got %s", aapl.Isin)
	}
}

// ─── Filtering Tests ─────────────────────────────────────────────────

func TestByExchange(t *testing.T) {
	xnas := testRegistry.ByExchange("XNAS")
	if len(xnas) == 0 {
		t.Fatal("Expected instruments on XNAS")
	}
	for _, inst := range xnas {
		if inst.Exchange != "XNAS" {
			t.Errorf("Expected XNAS, got %s", inst.Exchange)
		}
	}
}

func TestByExchangeNotFound(t *testing.T) {
	zzzz := testRegistry.ByExchange("ZZZZ")
	if len(zzzz) != 0 {
		t.Errorf("Expected 0 results, got %d", len(zzzz))
	}
}

func TestByAssetClass(t *testing.T) {
	etfs := testRegistry.ByAssetClass(AssetClassEtf)
	if len(etfs) == 0 {
		t.Fatal("Expected ETFs")
	}
	for _, inst := range etfs {
		if inst.AssetClass != AssetClassEtf {
			t.Errorf("Expected etf, got %s", inst.AssetClass)
		}
	}
}

func TestByAssetClassEquity(t *testing.T) {
	equities := testRegistry.ByAssetClass(AssetClassEquity)
	etfs := testRegistry.ByAssetClass(AssetClassEtf)
	total := len(equities) + len(etfs)
	if total != 50 {
		t.Errorf("Expected 50 total, got %d", total)
	}
}

func TestByCountry(t *testing.T) {
	us := testRegistry.ByCountry("US")
	if len(us) == 0 {
		t.Fatal("Expected US instruments")
	}
	for _, inst := range us {
		if inst.Country == nil || *inst.Country != "US" {
			t.Errorf("Expected US, got %v", inst.Country)
		}
	}
}

func TestByCurrency(t *testing.T) {
	usd := testRegistry.ByCurrency("USD")
	if len(usd) == 0 {
		t.Fatal("Expected USD instruments")
	}
	for _, inst := range usd {
		if inst.Currency != "USD" {
			t.Errorf("Expected USD, got %s", inst.Currency)
		}
	}
}

// ─── Aggregate Information Tests ─────────────────────────────────────

func TestExchanges(t *testing.T) {
	exchanges := testRegistry.Exchanges()
	if len(exchanges) != 9 {
		t.Errorf("Expected 9 exchanges, got %d", len(exchanges))
	}

	// Verify sorted
	for i := 1; i < len(exchanges); i++ {
		if exchanges[i-1] >= exchanges[i] {
			t.Errorf("Exchanges not sorted: %v", exchanges)
		}
	}

	// Verify key exchanges present
	found := make(map[string]bool)
	for _, e := range exchanges {
		found[e] = true
	}
	for _, expected := range []string{"XNAS", "XNYS", "XLON", "XTKS"} {
		if !found[expected] {
			t.Errorf("Missing exchange: %s", expected)
		}
	}
}

func TestCurrencies(t *testing.T) {
	currencies := testRegistry.Currencies()
	if len(currencies) != 7 {
		t.Errorf("Expected 7 currencies, got %d", len(currencies))
	}

	found := make(map[string]bool)
	for _, c := range currencies {
		found[c] = true
	}
	for _, expected := range []string{"USD", "EUR", "GBP", "JPY"} {
		if !found[expected] {
			t.Errorf("Missing currency: %s", expected)
		}
	}
}

func TestCountries(t *testing.T) {
	countries := testRegistry.Countries()
	if len(countries) != 8 {
		t.Errorf("Expected 8 countries, got %d", len(countries))
	}

	found := make(map[string]bool)
	for _, c := range countries {
		found[c] = true
	}
	for _, expected := range []string{"US", "GB", "JP", "DE"} {
		if !found[expected] {
			t.Errorf("Missing country: %s", expected)
		}
	}
}

// ─── Convenience Method Tests ────────────────────────────────────────

func TestIsinExists(t *testing.T) {
	if !testRegistry.IsinExists("US0378331005") {
		t.Error("Expected US0378331005 to exist")
	}
	if testRegistry.IsinExists("XX0000000000") {
		t.Error("Expected XX0000000000 to not exist")
	}
}

func TestTickerExists(t *testing.T) {
	if !testRegistry.TickerExists("AAPL", "") {
		t.Error("Expected AAPL to exist")
	}
	if testRegistry.TickerExists("ZZZZ", "") {
		t.Error("Expected ZZZZ to not exist")
	}
	if !testRegistry.TickerExists("PRU", "XLON") {
		t.Error("Expected PRU on XLON to exist")
	}
	if testRegistry.TickerExists("PRU", "ZZZZ") {
		t.Error("Expected PRU on ZZZZ to not exist")
	}
}

// ─── Coverage Tests ──────────────────────────────────────────────────

func TestIdentifierCoverage(t *testing.T) {
	coverage := testRegistry.IdentifierCoverage()

	if coverage.Isin.Covered != 50 {
		t.Errorf("Expected 50 ISINs, got %d", coverage.Isin.Covered)
	}
	if coverage.Isin.Percentage != 100.0 {
		t.Errorf("Expected 100%% ISIN coverage, got %.1f%%", coverage.Isin.Percentage)
	}

	if coverage.Cusip.Covered != 43 {
		t.Errorf("Expected 43 CUSIPs, got %d", coverage.Cusip.Covered)
	}

	if coverage.Sedol.Covered != 0 {
		t.Errorf("Expected 0 SEDOLs, got %d", coverage.Sedol.Covered)
	}

	if coverage.Figi.Covered != 49 {
		t.Errorf("Expected 49 FIGIs, got %d", coverage.Figi.Covered)
	}

	if coverage.Lei.Covered != 50 {
		t.Errorf("Expected 50 LEIs, got %d", coverage.Lei.Covered)
	}
}

func TestTickersWithMultipleListings(t *testing.T) {
	ambiguous := testRegistry.TickersWithMultipleListings()
	if len(ambiguous) != 1 {
		t.Errorf("Expected 1 ambiguous ticker, got %d", len(ambiguous))
	}
	if ambiguous[0] != "PRU" {
		t.Errorf("Expected PRU, got %s", ambiguous[0])
	}
}

// ─── Ticker Change Tests ─────────────────────────────────────────────

func TestTickerChangeMeta(t *testing.T) {
	meta, ok := testRegistry.ByIsin("US30303M1027")
	if !ok {
		t.Fatal("Expected META to be found")
	}
	if meta.Ticker != "META" {
		t.Errorf("Expected META, got %s", meta.Ticker)
	}

	// History should contain FB
	foundFB := false
	for _, event := range meta.History {
		if event.Ticker == "FB" {
			foundFB = true
		}
	}
	if !foundFB {
		t.Error("Expected history to contain FB")
	}
}

func TestTickerChangeIsinPermanent(t *testing.T) {
	meta, ok := testRegistry.ByIsin("US30303M1027")
	if !ok {
		t.Fatal("Expected META to be found")
	}
	if meta.Isin != "US30303M1027" {
		t.Errorf("Expected US30303M1027, got %s", meta.Isin)
	}
}

// ─── Multi-Exchange Listing Tests ────────────────────────────────────

func TestMultiExchangeListing(t *testing.T) {
	aapl, ok := testRegistry.ByIsin("US0378331005")
	if !ok {
		t.Fatal("Expected AAPL to be found")
	}

	if len(aapl.Listings) < 2 {
		t.Fatalf("Expected at least 2 listings, got %d", len(aapl.Listings))
	}

	foundXNAS := false
	foundXETR := false
	for _, listing := range aapl.Listings {
		if listing.Exchange == "XNAS" {
			foundXNAS = true
		}
		if listing.Exchange == "XETR" {
			foundXETR = true
		}
	}

	if !foundXNAS || !foundXETR {
		t.Error("Expected listings on XNAS and XETR")
	}
}

// ─── Error Handling Tests ────────────────────────────────────────────

func TestLoadNonexistentFile(t *testing.T) {
	_, err := LoadRegistry("/nonexistent/path/identifiers.json")
	if err == nil {
		t.Fatal("Expected error for nonexistent file")
	}
}

func TestLoadInvalidJSON(t *testing.T) {
	// Create temp file with invalid JSON
	tmpFile, err := os.CreateTemp("", "invalid_registry_*.json")
	if err != nil {
		t.Fatal(err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.WriteString("{ invalid json"); err != nil {
		t.Fatal(err)
	}
	tmpFile.Close()

	_, err = LoadRegistry(tmpFile.Name())
	if err == nil {
		t.Fatal("Expected error for invalid JSON")
	}
}

// ─── String Representation Tests ─────────────────────────────────────

func TestStringRepresentation(t *testing.T) {
	str := testRegistry.String()
	if str == "" {
		t.Error("String should not be empty")
	}

	// Should contain version and count
	if !contains(str, "1.0.0") {
		t.Errorf("Expected version in string: %s", str)
	}
	if !contains(str, "50") {
		t.Errorf("Expected count in string: %s", str)
	}
}

// ─── Helper ──────────────────────────────────────────────────────────

func contains(s string, substr string) bool {
	return len(s) >= len(substr) && indexOf(s, substr) >= 0
}

func indexOf(s string, substr string) int {
	for i := 0; i+len(substr) <= len(s); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}