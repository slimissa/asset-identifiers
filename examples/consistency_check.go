// Cross-language consistency check — Go side.
//
// Loads the synthetic test fixture, looks up every instrument by ISIN
// through the Go wrapper, and prints one tab-separated line per
// instrument: ISIN, ticker, name.
//
// See consistency_check.py for the full explanation of how this fits
// into the cross-language consistency check as a whole.
//
// Run:
//   cd examples
//   go run consistency_check.go ../tests/fixtures/identifiers.test.json

package main

import (
	"encoding/json"
	"fmt"
	"os"

	assetidentifiers "github.com/slimissa/asset-identifiers-go"
)

type fixtureFile struct {
	Instruments []struct {
		Isin string `json:"isin"`
	} `json:"instruments"`
}

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: consistency_check <fixture_path>")
		os.Exit(2)
	}
	fixturePath := os.Args[1]

	raw, err := os.ReadFile(fixturePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read fixture: %v\n", err)
		os.Exit(1)
	}

	var fixture fixtureFile
	if err := json.Unmarshal(raw, &fixture); err != nil {
		fmt.Fprintf(os.Stderr, "failed to parse fixture: %v\n", err)
		os.Exit(1)
	}

	registry, err := assetidentifiers.LoadRegistry(fixturePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load registry: %v\n", err)
		os.Exit(1)
	}

	for _, expected := range fixture.Instruments {
		actual, ok := registry.ByIsin(expected.Isin)
		if !ok {
			fmt.Printf("%s\tMISSING\tMISSING\n", expected.Isin)
		} else {
			fmt.Printf("%s\t%s\t%s\n", expected.Isin, actual.Ticker, actual.Name)
		}
	}
}
