#!/usr/bin/env python3
"""
Cross-language consistency check — Python side.

Loads the synthetic test fixture, looks up every instrument by ISIN
through the Python wrapper, and prints one tab-separated line per
instrument: ISIN, ticker, name.

A companion driver (run from CI) does the same in JavaScript, Rust,
and Go, and diffs all four outputs against the fixture itself and
against each other. This script does not do the comparison — it only
reports what this one wrapper returns, so a failure in one language
doesn't hide what the others say.

Run:
    cd examples
    python3 consistency_check.py ../tests/fixtures/identifiers.test.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "wrappers" / "python"))

from asset_identifiers import AssetRegistry


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: consistency_check.py <fixture_path>", file=sys.stderr)
        sys.exit(2)

    fixture_path = Path(sys.argv[1])
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture = json.load(f)

    registry = AssetRegistry(fixture_path)

    for expected in fixture["instruments"]:
        isin = expected["isin"]
        actual = registry.by_isin(isin)
        if actual is None:
            print(f"{isin}\tMISSING\tMISSING")
        else:
            print(f"{isin}\t{actual['ticker']}\t{actual['name']}")


if __name__ == "__main__":
    main()
