package assetidentifiers

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// ─── Test Setup ──────────────────────────────────────────────────────

// testRegistry loads the registry once for all tests.
var testRegistry = loadTestRegistry()

func loadTestRegistry() *AssetRegistry {
	registryPath := filepath.Join("..", "..", "tests", "fixtures", "identifiers.test.json")
	registry, err := LoadRegistry(registryPath)
	if err != nil {
		panic("Failed to load test registry: " + err.Error())
	}
	return registry
}

// ─── Fixture-derived anchors ─────────────────────────────────────────
//
// These variables hold the values the tests assert against. They are
// derived from the fixture at runtime, so a fixture change cannot leave
// the tests silently wrong. If a required anchor is missing, the tests
// fail loudly instead of comparing against a stale hardcoded string.

var (
	testa   = mustByTickerExchange("TESTA", "XNAS")
	newtick = mustByTickerExchange("NEWTICK", "XNAS")
	multi   = mustByTickerExchange("MULTI", "XNAS")
	dupUS   = mustByTickerExchange("DUP", "XNAS")
	dupUK   = mustByTickerExchange("DUP", "XLON")
	etfSyn  = mustByTickerExchange("ETFSYN", "XNAS")
)

func mustByTickerExchange(ticker, exchange string) *Instrument {
	results := testRegistry.ByTicker(ticker, exchange)
	if len(results) != 1 {
		panic(fmt.Sprintf("fixture missing or ambiguous: %s@%s (got %d)", ticker, exchange, len(results)))
	}
	return results[0]
}

// ─── Registry Loading Tests ──────────────────────────────────────────

func TestRegistryLoads(t *testing.T) {
	if testRegistry == nil {
		t.Fatal("Registry should not be nil")
	}
}

func TestRegistryCount(t *testing.T) {
	expectedCount := len(testRegistry.All())
	if testRegistry.Count() != expectedCount {
		t.Errorf("Expected count to equal All() length, got %d vs %d", testRegistry.Count(), expectedCount)
	}
}

func TestRegistryPath(t *testing.T) {
	path := testRegistry.Path()
	if path == "" {
		t.Error("Path should not be empty")
	}
}

func TestRegistryVersion(t *testing.T) {
	want := testRegistry.Meta().Version
	if testRegistry.Version() != want {
		t.Errorf("Expected version %s, got %s", want, testRegistry.Version())
	}
}

func TestRegistryMeta(t *testing.T) {
	meta := testRegistry.Meta()
	if meta == nil {
		t.Fatal("Meta should not be nil")
	}
	expectedCount := len(testRegistry.All())
	if meta.Count != expectedCount {
		t.Errorf("Expected meta.count to equal All() length, got %d vs %d", meta.Count, expectedCount)
	}
	if meta.Version == "" {
		t.Error("Expected meta.version to be non-empty")
	}
}

// ─── ISIN Lookup Tests ───────────────────────────────────────────────

func TestByIsinFound(t *testing.T) {
	got, ok := testRegistry.ByIsin(testa.Isin)
	if !ok {
		t.Fatalf("Expected %s to be found by ISIN", testa.Ticker)
	}
	if got.Ticker != testa.Ticker {
		t.Errorf("Expected ticker %s, got %s", testa.Ticker, got.Ticker)
	}
	if got.Name != testa.Name {
		t.Errorf("Expected name %q, got %q", testa.Name, got.Name)
	}
	if got.Currency != testa.Currency {
		t.Errorf("Expected currency %s, got %s", testa.Currency, got.Currency)
	}
	if got.Exchange != testa.Exchange {
		t.Errorf("Expected exchange %s, got %s", testa.Exchange, got.Exchange)
	}
}

func TestByIsinNotFound(t *testing.T) {
	_, ok := testRegistry.ByIsin("XX0000000000")
	if ok {
		t.Error("Expected XX0000000000 to not be found")
	}
}

func TestByIsinCaseInsensitive(t *testing.T) {
	lower := lowerAscii(testa.Isin)
	got, ok := testRegistry.ByIsin(lower)
	if !ok {
		t.Fatalf("Expected lowercase ISIN %s to be found", lower)
	}
	if got.Ticker != testa.Ticker {
		t.Errorf("Expected %s, got %s", testa.Ticker, got.Ticker)
	}
}

func TestByIsinInternational(t *testing.T) {
	t.Skip("international instruments not in synthetic fixture")
}

// ─── CUSIP Lookup Tests ──────────────────────────────────────────────

func TestByCusipFound(t *testing.T) {
	if testa.Cusip == nil {
		t.Fatal("fixture TESTA has no CUSIP; test is meaningless")
	}
	got, ok := testRegistry.ByCusip(*testa.Cusip)
	if !ok {
		t.Fatalf("Expected %s to be found by CUSIP", testa.Ticker)
	}
	if got.Isin != testa.Isin {
		t.Errorf("Expected ISIN %s, got %s", testa.Isin, got.Isin)
	}
}

func TestByCusipNotFound(t *testing.T) {
	_, ok := testRegistry.ByCusip("999999999")
	if ok {
		t.Error("Expected 999999999 to not be found")
	}
}

// ─── FIGI Lookup Tests ───────────────────────────────────────────────

func TestByFigiFound(t *testing.T) {
	if testa.Figi == nil {
		t.Fatal("fixture TESTA has no FIGI; test is meaningless")
	}
	got, ok := testRegistry.ByFigi(*testa.Figi)
	if !ok {
		t.Fatalf("Expected %s to be found by FIGI", testa.Ticker)
	}
	if got.Isin != testa.Isin {
		t.Errorf("Expected ISIN %s, got %s", testa.Isin, got.Isin)
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
	if testa.Lei == nil {
		t.Fatal("fixture TESTA has no LEI; test is meaningless")
	}
	results := testRegistry.ByLei(*testa.Lei)
	if len(results) == 0 {
		t.Fatalf("Expected %s to be found by LEI", testa.Ticker)
	}
	found := false
	for _, inst := range results {
		if inst.Ticker == testa.Ticker {
			found = true
		}
	}
	if !found {
		t.Errorf("Expected %s in LEI results, got %d instrument(s)", testa.Ticker, len(results))
	}
}

func TestByLeiNotFound(t *testing.T) {
	if len(testRegistry.ByLei("00000000000000000000")) != 0 {
		t.Error("Expected LEI to not be found")
	}
}

// ─── Ticker Lookup Tests ─────────────────────────────────────────────

func TestByTickerWithExchange(t *testing.T) {
	results := testRegistry.ByTicker(testa.Ticker, testa.Exchange)
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Isin != testa.Isin {
		t.Errorf("Expected ISIN %s, got %s", testa.Isin, results[0].Isin)
	}
}

func TestByTickerWithoutExchange(t *testing.T) {
	results := testRegistry.ByTicker(testa.Ticker, "")
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Ticker != testa.Ticker {
		t.Errorf("Expected %s, got %s", testa.Ticker, results[0].Ticker)
	}
}

func TestByTickerAmbiguous(t *testing.T) {
	results := testRegistry.ByTicker("DUP", "")
	if len(results) != 2 {
		t.Fatalf("Expected 2 results for DUP, got %d", len(results))
	}
	exchanges := map[string]bool{}
	for _, inst := range results {
		exchanges[inst.Exchange] = true
	}
	if !exchanges["XLON"] || !exchanges["XNAS"] {
		t.Errorf("Expected XLON and XNAS, got %v", exchanges)
	}
}

func TestByTickerDisambiguateLondon(t *testing.T) {
	results := testRegistry.ByTicker(dupUK.Ticker, dupUK.Exchange)
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Isin != dupUK.Isin {
		t.Errorf("Expected ISIN %s, got %s", dupUK.Isin, results[0].Isin)
	}
	if results[0].Currency != dupUK.Currency {
		t.Errorf("Expected %s, got %s", dupUK.Currency, results[0].Currency)
	}
}

func TestByTickerDisambiguateNewYork(t *testing.T) {
	results := testRegistry.ByTicker(dupUS.Ticker, dupUS.Exchange)
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	if results[0].Isin != dupUS.Isin {
		t.Errorf("Expected ISIN %s, got %s", dupUS.Isin, results[0].Isin)
	}
	if results[0].Currency != dupUS.Currency {
		t.Errorf("Expected %s, got %s", dupUS.Currency, results[0].Currency)
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
	got, ok := testRegistry.ByTickerExchange(testa.Ticker, testa.Exchange)
	if !ok {
		t.Fatalf("Expected %s to be found", testa.Ticker)
	}
	if got.Isin != testa.Isin {
		t.Errorf("Expected %s, got %s", testa.Isin, got.Isin)
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
	if len(testRegistry.ByExchange("ZZZZ")) != 0 {
		t.Error("Expected 0 results for ZZZZ")
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
	expectedCount := len(testRegistry.All())
	if total != expectedCount {
		t.Errorf("Expected total to equal All() length, got %d vs %d", total, expectedCount)
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
	// Fixture primary listings: XNAS, XLON
	expected := map[string]bool{"XNAS": false, "XLON": false}
	for _, e := range exchanges {
		if _, ok := expected[e]; ok {
			expected[e] = true
		}
	}
	for e, found := range expected {
		if !found {
			t.Errorf("Missing exchange: %s", e)
		}
	}
}

func TestCurrencies(t *testing.T) {
	currencies := testRegistry.Currencies()
	// Fixture currencies: USD, GBP
	expected := map[string]bool{"USD": false, "GBP": false}
	for _, c := range currencies {
		if _, ok := expected[c]; ok {
			expected[c] = true
		}
	}
	for c, found := range expected {
		if !found {
			t.Errorf("Missing currency: %s", c)
		}
	}
}

func TestCountries(t *testing.T) {
	countries := testRegistry.Countries()
	if len(countries) == 0 {
		t.Fatal("Expected at least one country")
	}
	found := map[string]bool{}
	for _, c := range countries {
		found[c] = true
	}
	for _, expected := range []string{"US", "GB"} {
		if !found[expected] {
			t.Errorf("Missing country: %s", expected)
		}
	}
}

// ─── Convenience Method Tests ────────────────────────────────────────

func TestIsinExists(t *testing.T) {
	if !testRegistry.IsinExists(testa.Isin) {
		t.Errorf("Expected %s to exist", testa.Isin)
	}
	if testRegistry.IsinExists("XX0000000000") {
		t.Error("Expected XX0000000000 to not exist")
	}
}

func TestTickerExists(t *testing.T) {
	if !testRegistry.TickerExists(testa.Ticker, testa.Exchange) {
		t.Errorf("Expected %s to exist", testa.Ticker)
	}
	if testRegistry.TickerExists("ZZZZ", "") {
		t.Error("Expected ZZZZ to not exist")
	}
	if !testRegistry.TickerExists(dupUK.Ticker, dupUK.Exchange) {
		t.Errorf("Expected %s on %s to exist", dupUK.Ticker, dupUK.Exchange)
	}
	if testRegistry.TickerExists(dupUS.Ticker, "ZZZZ") {
		t.Errorf("Expected %s on ZZZZ to not exist", dupUS.Ticker)
	}
}

// ─── Coverage Tests ──────────────────────────────────────────────────

func TestIdentifierCoverage(t *testing.T) {
	coverage := testRegistry.IdentifierCoverage()

	expectedCount := len(testRegistry.All())
	if coverage.Isin.Covered != expectedCount {
		t.Errorf("Expected ISIN coverage to equal All() length, got %d vs %d", coverage.Isin.Covered, expectedCount)
	}
	if coverage.Isin.Percentage != 100.0 {
		t.Errorf("Expected 100%% ISIN coverage, got %.1f%%", coverage.Isin.Percentage)
	}

	expectedCusip := 0
	for _, inst := range testRegistry.All() {
		if inst.Cusip != nil {
			expectedCusip++
		}
	}
	if coverage.Cusip.Covered != expectedCusip {
		t.Errorf("Expected CUSIP coverage to match data, got %d vs %d", coverage.Cusip.Covered, expectedCusip)
	}

	if coverage.Sedol.Covered != 0 {
		t.Errorf("Expected 0 SEDOLs, got %d", coverage.Sedol.Covered)
	}

	expectedFigi := 0
	for _, inst := range testRegistry.All() {
		if inst.Figi != nil {
			expectedFigi++
		}
	}
	if coverage.Figi.Covered != expectedFigi {
		t.Errorf("Expected FIGI coverage to match data, got %d vs %d", coverage.Figi.Covered, expectedFigi)
	}

	expectedLei := 0
	for _, inst := range testRegistry.All() {
		if inst.Lei != nil {
			expectedLei++
		}
	}
	if coverage.Lei.Covered != expectedLei {
		t.Errorf("Expected LEI coverage to match data, got %d vs %d", coverage.Lei.Covered, expectedLei)
	}
}

func TestTickersWithMultipleListings(t *testing.T) {
	ambiguous := testRegistry.TickersWithMultipleListings()
	if len(ambiguous) != 1 {
		t.Errorf("Expected 1 ambiguous ticker, got %d", len(ambiguous))
	}
	if len(ambiguous) > 0 && ambiguous[0] != "DUP" {
		t.Errorf("Expected DUP, got %s", ambiguous[0])
	}
}

// ─── Ticker Change Tests ─────────────────────────────────────────────

func TestTickerChangeMeta(t *testing.T) {
	got, ok := testRegistry.ByIsin(newtick.Isin)
	if !ok {
		t.Fatalf("Expected %s to be found", newtick.Ticker)
	}
	if got.Ticker != newtick.Ticker {
		t.Errorf("Expected %s, got %s", newtick.Ticker, got.Ticker)
	}
	foundOld := false
	for _, event := range got.History {
		if event.Ticker == "OLDTICK" {
			foundOld = true
		}
	}
	if !foundOld {
		t.Error("Expected history to contain OLDTICK")
	}
}

func TestTickerChangeIsinPermanent(t *testing.T) {
	got, ok := testRegistry.ByIsin(newtick.Isin)
	if !ok {
		t.Fatalf("Expected %s to be found", newtick.Ticker)
	}
	if got.Isin != newtick.Isin {
		t.Errorf("Expected %s, got %s", newtick.Isin, got.Isin)
	}
}

// ─── Multi-Exchange Listing Tests ────────────────────────────────────

func TestMultiExchangeListing(t *testing.T) {
	got, ok := testRegistry.ByIsin(multi.Isin)
	if !ok {
		t.Fatalf("Expected %s to be found", multi.Ticker)
	}
	if len(got.Listings) < 2 {
		t.Fatalf("Expected at least 2 listings, got %d", len(got.Listings))
	}
	found := map[string]bool{}
	for _, listing := range got.Listings {
		found[listing.Exchange] = true
	}
	if !found["XNAS"] || !found["XETR"] {
		t.Errorf("Expected listings on XNAS and XETR, got %v", found)
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
	if !contains(str, testRegistry.Version()) {
		t.Errorf("Expected version in string: %s", str)
	}
	if !contains(str, fmt.Sprint(testRegistry.Count())) {
		t.Errorf("Expected count in string: %s", str)
	}
}

// ─── Helpers ─────────────────────────────────────────────────────────

func contains(s, substr string) bool {
	return indexOf(s, substr) >= 0
}

func indexOf(s, substr string) int {
	for i := 0; i+len(substr) <= len(s); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

func lowerAscii(s string) string {
	out := []byte(s)
	for i := range out {
		if 'A' <= out[i] && out[i] <= 'Z' {
			out[i] += 'a' - 'A'
		}
	}
	return string(out)
}
