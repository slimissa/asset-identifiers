// Asset Identifier Registry — Go usage example.
//
// This example demonstrates all major features of the
// Go wrapper for the asset identifier registry.
//
// Run:
//   cd examples
//   go run go_lookup.go

package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	assetidentifiers "github.com/slimissa/asset-identifiers-go"
)

func main() {
	// ─── Load the Registry ──────────────────────────────────────────

	// Path relative to examples/ directory
	registryPath := filepath.Join("..", "identifiers.json")

	registry, err := assetidentifiers.LoadRegistry(registryPath)
	if err != nil {
		log.Fatalf("Failed to load registry: %v", err)
	}

	printSection("Registry Overview")
	fmt.Printf("Version:    %s\n", registry.Version())
	fmt.Printf("Generated:  %s\n", registry.Generated())
	fmt.Printf("Instruments: %d\n", registry.Count())
	fmt.Printf("Path:       %s\n", registry.Path())
	fmt.Printf("Sources:    %v\n", registry.Sources())

	// ─── Lookup by ISIN ─────────────────────────────────────────────

	printSection("Lookup by ISIN")

	aapl, ok := registry.ByIsin("US0378331005")
	if !ok {
		log.Fatal("AAPL not found by ISIN")
	}

	fmt.Printf("Ticker:      %s\n", aapl.Ticker)
	fmt.Printf("Name:        %s\n", aapl.Name)
	fmt.Printf("Exchange:    %s\n", aapl.Exchange)
	fmt.Printf("Currency:    %s\n", aapl.Currency)
	fmt.Printf("Asset class: %s\n", aapl.AssetClass)
	fmt.Printf("CUSIP:       %v\n", derefOrNil(aapl.Cusip))
	fmt.Printf("FIGI:        %v\n", derefOrNil(aapl.Figi))
	fmt.Printf("LEI:         %v\n", derefOrNil(aapl.Lei))
	fmt.Printf("Active:      %t\n", aapl.Active)
	fmt.Printf("Country:     %v\n", derefOrNil(aapl.Country))

	// ─── Lookup by Other Identifiers ────────────────────────────────

	printSection("Lookup by Other Identifiers")

	if msft, ok := registry.ByCusip("594918104"); ok {
		fmt.Printf("By CUSIP 594918104 → %s (%s)\n", msft.Ticker, msft.Name)
	}

	if aaplFigi, ok := registry.ByFigi("BBG000B9XRY4"); ok {
		fmt.Printf("By FIGI BBG000B9XRY4 → %s (%s)\n", aaplFigi.Ticker, aaplFigi.Name)
	}

	if aaplLei, ok := registry.ByLei("HWUPKR0MPOU8FGXBT394"); ok {
		fmt.Printf("By LEI HWUPKR... → %s (%s)\n", aaplLei.Ticker, aaplLei.Name)
	}

	// ─── Ticker Lookup ──────────────────────────────────────────────

	printSection("Ticker Lookup")

	// Single result with exchange
	if aaplTicker, ok := registry.ByTickerExchange("AAPL", "XNAS"); ok {
		fmt.Printf("AAPL on XNAS → %s\n", aaplTicker.Isin)
	}

	// Ambiguous ticker without exchange
	pruAll := registry.ByTicker("PRU", "")
	fmt.Printf("PRU (all exchanges): %d results\n", len(pruAll))
	for _, pru := range pruAll {
		fmt.Printf("  %s on %s → %s (%s)\n", pru.Ticker, pru.Exchange, pru.Isin, pru.Name)
	}

	// Disambiguated
	if pruLondon, ok := registry.ByTickerExchange("PRU", "XLON"); ok {
		fmt.Printf("PRU on XLON → %s (%s, %s)\n", pruLondon.Isin, pruLondon.Name, pruLondon.Currency)
	}

	if pruNyse, ok := registry.ByTickerExchange("PRU", "XNYS"); ok {
		fmt.Printf("PRU on XNYS → %s (%s, %s)\n", pruNyse.Isin, pruNyse.Name, pruNyse.Currency)
	}

	// ─── Filtering ──────────────────────────────────────────────────

	printSection("Filtering")

	nasdaq := registry.ByExchange("XNAS")
	fmt.Printf("NASDAQ (XNAS): %d instruments\n", len(nasdaq))

	etfs := registry.ByAssetClass(assetidentifiers.AssetClassEtf)
	fmt.Printf("ETFs: %d instruments\n", len(etfs))
	for _, etf := range etfs {
		fmt.Printf("  %s (%s)\n", etf.Ticker, etf.Name)
	}

	usInstruments := registry.ByCountry("US")
	fmt.Printf("US instruments: %d\n", len(usInstruments))

	usdInstruments := registry.ByCurrency("USD")
	fmt.Printf("USD instruments: %d\n", len(usdInstruments))

	// ─── Aggregate Information ──────────────────────────────────────

	printSection("Aggregate Information")

	fmt.Printf("Exchanges:   %v\n", registry.Exchanges())
	fmt.Printf("Currencies:  %v\n", registry.Currencies())
	fmt.Printf("Countries:   %v\n", registry.Countries())

	// ─── Identifier Coverage ────────────────────────────────────────

	printSection("Identifier Coverage")

	coverage := registry.IdentifierCoverage()

	fmt.Printf("ISIN:  %d/%d (%.1f%%)\n", coverage.Isin.Covered, coverage.Isin.Total, coverage.Isin.Percentage)
	fmt.Printf("CUSIP: %d/%d (%.1f%%)\n", coverage.Cusip.Covered, coverage.Cusip.Total, coverage.Cusip.Percentage)
	fmt.Printf("SEDOL: %d/%d (%.1f%%)\n", coverage.Sedol.Covered, coverage.Sedol.Total, coverage.Sedol.Percentage)
	fmt.Printf("FIGI:  %d/%d (%.1f%%)\n", coverage.Figi.Covered, coverage.Figi.Total, coverage.Figi.Percentage)
	fmt.Printf("LEI:   %d/%d (%.1f%%)\n", coverage.Lei.Covered, coverage.Lei.Total, coverage.Lei.Percentage)

	// ─── Ticker Changes ─────────────────────────────────────────────

	printSection("Ticker Changes")

	meta, ok := registry.ByIsin("US30303M1027")
	if !ok {
		log.Fatal("META not found")
	}

	fmt.Printf("Current ticker: %s\n", meta.Ticker)
	fmt.Printf("ISIN:           %s (unchanged)\n", meta.Isin)
	fmt.Println("History:")
	for _, event := range meta.History {
		fmt.Printf("  %s  %s  %s", event.Ticker, event.ChangeDate, event.ChangeType)
		if event.Reason != nil {
			fmt.Printf("  (%s)", *event.Reason)
		}
		fmt.Println()
	}

	// ─── Multi-Exchange Listings ────────────────────────────────────

	printSection("Multi-Exchange Listings")

	for _, listing := range aapl.Listings {
		fmt.Printf("%s: %s (%s, %s)\n", listing.Exchange, listing.Ticker, listing.Currency, listing.Status)
	}

	// ─── Ambiguous Tickers ──────────────────────────────────────────

	printSection("Ambiguous Tickers")

	ambiguous := registry.TickersWithMultipleListings()
	fmt.Printf("Tickers with multiple listings: %v\n", ambiguous)

	// ─── Existence Checks ───────────────────────────────────────────

	printSection("Existence Checks")

	fmt.Printf("US0378331005 exists: %t\n", registry.IsinExists("US0378331005"))
	fmt.Printf("XX0000000000 exists: %t\n", registry.IsinExists("XX0000000000"))
	fmt.Printf("AAPL on XNAS exists: %t\n", registry.TickerExists("AAPL", "XNAS"))
	fmt.Printf("PRU anywhere exists: %t\n", registry.TickerExists("PRU", ""))
	fmt.Printf("ZZZZ exists:         %t\n", registry.TickerExists("ZZZZ", ""))

	// ─── Iteration ──────────────────────────────────────────────────

	printSection("Iteration (first 10)")

	count := 0
	for _, inst := range registry.All() {
		if count >= 10 {
			fmt.Println("  ...")
			break
		}
		fmt.Printf("  %s (%s): %s\n", inst.Ticker, inst.Exchange, inst.Isin)
		count++
	}

	// ─── String Representation ──────────────────────────────────────

	printSection("String Representation")

	fmt.Printf("%s\n", registry)

	fmt.Println()
	fmt.Println("Example complete.")
}

// ─── Helpers ──────────────────────────────────────────────────────────

func printSection(title string) {
	fmt.Println()
	fmt.Println("══════════════════════════════════════════════════════════")
	fmt.Printf("  %s\n", title)
	fmt.Println("══════════════════════════════════════════════════════════")
}

func derefOrNil(s *string) string {
	if s == nil {
		return "nil"
	}
	return *s
}

// Ensure os is used (for future extension)
var _ = os.Args